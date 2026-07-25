"""Safely copy and edit trial-specific ELM NetCDF parameter files.

The current API intentionally changes one scalar or one element of a
one-dimensional variable in each output file.

TODO: Add a batch-edit API when the BOA wrapper supports multiple parameters
from the same staged ELM file.
TODO: Generalize the index representation if a real parameter target requires
editing a multidimensional variable.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import shutil
import tempfile

from netCDF4 import Dataset
import numpy as np


PathLike = str | Path


@dataclass(frozen=True)
class ELMParameterEdit:
    """Audit record for one change to a copied ELM parameter file."""

    source_path: str
    output_path: str
    variable: str
    index: int | None
    original_value: float
    new_value: float
    source_sha256: str
    output_sha256: str


def edit_elm_parameter(
    source_path: PathLike,
    output_path: PathLike,
    *,
    variable: str,
    value: float,
    index: int | None = None,
    expected_source_value: float | None = None,
) -> ELMParameterEdit:
    """Copy an ELM parameter file and change exactly one numeric value.

    Array parameters require an explicit one-dimensional ``index``. Scalar
    parameters require ``index=None``. The source is opened read-only and
    checked before and after the operation. The edited copy is first written to
    a temporary file in the output directory, validated, and then moved to the
    requested path.

    ``expected_source_value`` optionally lets callers reject an unexpected
    source file before making an edit. Existing output files are never
    intentionally replaced.

    TODO: Replace this single-edit operation with, or build it upon, a
    batch-edit operation when one trial needs to change multiple variables in
    the same NetCDF file.
    """
    source = Path(source_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()

    if not source.is_file():
        raise FileNotFoundError(f"ELM parameter file does not exist: {source}")
    if source == output:
        raise ValueError("The output parameter file must differ from the source file")
    if output.exists():
        raise FileExistsError(f"Output parameter file already exists: {output}")
    if not variable:
        raise ValueError("variable must be a non-empty NetCDF variable name")
    if not math.isfinite(float(value)):
        raise ValueError("ELM parameter value must be finite")

    source_sha256 = _sha256(source)
    original_value = _read_parameter(source, variable=variable, index=index)
    if expected_source_value is not None and not _values_equal(
        original_value, float(expected_source_value)
    ):
        raise ValueError(
            f"ELM parameter {variable}{_format_index(index)} has value "
            f"{original_value!r}, not the expected source value "
            f"{expected_source_value!r}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        shutil.copy2(source, temporary_path)
        with Dataset(temporary_path, "r+") as dataset:
            target = _get_target(dataset, variable=variable, index=index)
            if index is None:
                target.assignValue(value)
            else:
                target[index] = value
            dataset.sync()

        written_value = _read_parameter(
            temporary_path,
            variable=variable,
            index=index,
        )
        if not _values_equal(written_value, float(value)):
            raise RuntimeError(
                f"ELM parameter {variable}{_format_index(index)} was written as "
                f"{written_value!r}, not the requested value {value!r}"
            )

        current_source_sha256 = _sha256(source)
        if current_source_sha256 != source_sha256:
            raise RuntimeError(
                f"Source ELM parameter file changed during the edit: {source}"
            )

        if output.exists():
            raise FileExistsError(f"Output parameter file already exists: {output}")
        temporary_path.replace(output)
    finally:
        temporary_path.unlink(missing_ok=True)

    return ELMParameterEdit(
        source_path=str(source),
        output_path=str(output),
        variable=variable,
        index=index,
        original_value=original_value,
        new_value=written_value,
        source_sha256=source_sha256,
        output_sha256=_sha256(output),
    )


def _get_target(dataset: Dataset, *, variable: str, index: int | None):
    if variable not in dataset.variables:
        raise KeyError(f"NetCDF variable {variable!r} is not present")

    target = dataset.variables[variable]
    if index is None:
        if target.ndim != 0:
            raise ValueError(
                f"NetCDF variable {variable!r} has shape {target.shape}; "
                "an explicit index is required"
            )
    else:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("ELM parameter index must be an integer")
        if target.ndim != 1:
            raise ValueError(
                f"Indexed NetCDF variable {variable!r} must be one-dimensional; "
                f"found shape {target.shape}"
            )
        if index < 0 or index >= target.shape[0]:
            raise IndexError(
                f"Index {index} is outside NetCDF variable {variable!r} "
                f"with shape {target.shape}"
            )
    return target


def _read_parameter(path: Path, *, variable: str, index: int | None) -> float:
    with Dataset(path, "r") as dataset:
        target = _get_target(dataset, variable=variable, index=index)
        raw_value = target.getValue() if index is None else target[index]
        if np.ma.is_masked(raw_value):
            raise ValueError(
                f"ELM parameter {variable}{_format_index(index)} is masked"
            )
        value = float(np.asarray(raw_value).item())
        if not math.isfinite(value):
            raise ValueError(
                f"ELM parameter {variable}{_format_index(index)} is not finite"
            )
        return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _values_equal(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-7, abs_tol=0.0)


def _format_index(index: int | None) -> str:
    return "" if index is None else f"[{index}]"

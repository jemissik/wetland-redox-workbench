"""Utilities for opening and inspecting ELM history output.

The functions here are intentionally independent of plotting, observations,
optimization, and any particular ELM case.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np
import xarray as xr


PathLike = str | Path


def find_history_files(
    run_dir: PathLike,
    *,
    stream: str = "h0",
) -> list[Path]:
    """Return one case's sorted ELM history files from a run directory.

    Parameters
    ----------
    run_dir
        Directory containing ELM history output.
    stream
        ELM history stream, such as ``h0`` or ``h1``.
    """
    run_dir = Path(run_dir)
    files = sorted(run_dir.glob(f"*.elm.{stream}.*.nc"))
    if not files:
        raise FileNotFoundError(
            f"No ELM {stream} history files found in {run_dir}"
        )

    marker = f".elm.{stream}."
    case_names = {path.name.rsplit(marker, 1)[0] for path in files}
    if len(case_names) != 1:
        raise ValueError(
            f"Run directory contains ELM {stream} files from multiple cases: "
            f"{sorted(case_names)}"
        )
    return files


def history_time_size(path: PathLike) -> int:
    """Return a history file's number of time records without decoding time."""
    with xr.open_dataset(path, decode_times=False, mask_and_scale=False) as dataset:
        return int(dataset.sizes.get("time", 0))


def nonempty_history_files(files: Iterable[PathLike]) -> tuple[list[Path], list[Path]]:
    """Split history files into nonempty and zero-time-record lists."""
    nonempty: list[Path] = []
    empty: list[Path] = []
    for file in map(Path, files):
        if history_time_size(file) > 0:
            nonempty.append(file)
        else:
            empty.append(file)
    return nonempty, empty


def _drop_duplicate_times(dataset: xr.Dataset) -> xr.Dataset:
    time_index = dataset.indexes["time"]
    return dataset.isel(time=~time_index.duplicated())


def _select_variables(dataset: xr.Dataset, variables: Sequence[str]) -> xr.Dataset:
    """Select requested variables, retaining time bounds when available.

    Raise ``KeyError`` if any requested variable is missing.
    """
    missing = [name for name in variables if name not in dataset]
    if missing:
        raise KeyError(f"ELM history output is missing variables: {missing}")
    selected = list(variables)
    if "time_bounds" in dataset and "time_bounds" not in selected:
        selected.append("time_bounds")
    return dataset[selected]


def open_history(
    files: Iterable[PathLike],
    *,
    variables: Sequence[str] | None = None,
    lndgrid_index: int | None = 0,
    start: str | None = None,
    end: str | None = None,
    drop_duplicate_times: bool = True,
) -> xr.Dataset:
    """Open one or more ELM history files as a time-ordered dataset.

    Zero-time-record files are skipped, and the remaining files are opened
    lazily through :func:`xarray.open_mfdataset`, which requires Dask. Use the
    returned dataset as a context manager or call :meth:`xarray.Dataset.close`
    when finished.

    By default, the first ``lndgrid`` entry is selected because this project
    primarily uses single-site ELM cases. Pass ``lndgrid_index=None`` to retain
    that dimension.
    """
    paths = [Path(file) for file in files]
    if not paths:
        raise ValueError("At least one ELM history file is required")

    nonempty, empty = nonempty_history_files(paths)
    if not nonempty:
        raise ValueError(
            f"Found {len(paths)} ELM history file(s), but all have zero time records"
        )

    source_dataset = xr.open_mfdataset(
        nonempty,
        combine="nested",
        concat_dim="time",
        chunks={"time": -1},
        data_vars="minimal",
        coords="minimal",
        compat="override",
        join="override",
        parallel=False,
        decode_times=True,
        mask_and_scale=True,
    )
    dataset = source_dataset

    try:
        dataset = dataset.sortby("time")
        if drop_duplicate_times:
            dataset = _drop_duplicate_times(dataset)
        if lndgrid_index is not None and "lndgrid" in dataset.dims:
            dataset = dataset.isel(lndgrid=lndgrid_index)
        if variables is not None:
            dataset = _select_variables(dataset, variables)
        if start is not None or end is not None:
            dataset = dataset.sel(time=slice(start, end))
        dataset.attrs.update(
            {
                "history_file_count": len(nonempty),
                "empty_history_files_skipped": len(empty),
                "history_files": "\n".join(str(path) for path in nonempty),
            }
        )
    except Exception:
        source_dataset.close()
        raise

    if dataset is not source_dataset:
        dataset.set_close(source_dataset.close)
    return dataset


def open_case_history(
    run_dir: PathLike,
    *,
    stream: str = "h0",
    **kwargs,
) -> xr.Dataset:
    """Find and open an ELM case's history files from its run directory.

    Use the returned dataset as a context manager or call
    :meth:`xarray.Dataset.close` when finished.
    """
    files = find_history_files(run_dir, stream=stream)
    dataset = open_history(files, **kwargs)
    dataset.attrs["run_dir"] = str(Path(run_dir))
    dataset.attrs["history_stream"] = stream
    return dataset


def scalar_timeseries(dataset: xr.Dataset, variable: str) -> xr.DataArray:
    """Return a variable as a one-dimensional time series.

    Singleton dimensions are removed, but non-singleton dimensions other than
    time raise an error so a depth, column, or PFT reduction is never hidden.
    """
    if variable not in dataset:
        raise KeyError(f"Variable {variable!r} is not present in the dataset")
    series = dataset[variable].squeeze(drop=True)
    extra_dims = [dim for dim in series.dims if dim != "time"]
    if extra_dims:
        raise ValueError(
            f"Variable {variable!r} is not a scalar time series; "
            f"remaining dimensions are {extra_dims}"
        )
    if "time" not in series.dims:
        raise ValueError(f"Variable {variable!r} has no time dimension")
    return series.transpose("time")


def depth_dimension(data: xr.DataArray) -> str:
    """Return the recognized ELM soil-depth dimension for a data array."""
    for dimension in ("levdcmp", "levgrnd", "levsoi", "levlak"):
        if dimension in data.dims:
            return dimension
    raise ValueError(f"No recognized ELM depth dimension in {data.dims}")


def normalize_history_time(
    dataset: xr.Dataset,
    *,
    position: str = "end",
) -> xr.Dataset:
    """Replace ELM's decoded time coordinate with interval-based timestamps.

    Each ELM history record represents an interval described by
    ``time_bounds``. The file's lower-precision ``time`` coordinate can decode
    to timestamps that are several seconds earlier or later than the intended
    interval boundary. These offsets can interfere with temporal aggregation
    and model-observation alignment.

    This function labels each record using the start, midpoint, or end of its
    ``time_bounds`` interval. It returns a new dataset object and does not
    modify the input dataset or source NetCDF files. The returned dataset
    shares lazy data and its close operation with the input dataset.

    Parameters
    ----------
    dataset
        Decoded ELM history dataset containing ``time`` and ``time_bounds``.
    position
        Representative point within each interval: ``"start"``,
        ``"midpoint"``, or ``"end"``.
    """
    valid_positions = {"start", "midpoint", "end"}
    if position not in valid_positions:
        raise ValueError(
            f"Unsupported interval position {position!r}; "
            f"choose one of {sorted(valid_positions)}"
        )
    if "time" not in dataset.coords:
        raise ValueError("Dataset has no time coordinate")
    if "time_bounds" not in dataset:
        raise ValueError("Dataset has no time_bounds variable")

    bounds = dataset["time_bounds"]
    if "time" not in bounds.dims:
        raise ValueError("time_bounds does not use the time dimension")
    interval_dims = [dimension for dimension in bounds.dims if dimension != "time"]
    if len(interval_dims) != 1 or bounds.sizes[interval_dims[0]] != 2:
        raise ValueError(
            "time_bounds must have one two-element interval dimension; "
            f"found dimensions {bounds.dims} with sizes {dict(bounds.sizes)}"
        )

    interval_dim = interval_dims[0]
    starts = bounds.isel({interval_dim: 0}).values
    ends = bounds.isel({interval_dim: 1}).values
    if position == "start":
        normalized = starts
    elif position == "end":
        normalized = ends
    else:
        normalized = np.asarray(
            [start + (end - start) / 2 for start, end in zip(starts, ends)]
        )

    result = dataset.copy(deep=False)
    original_time = dataset["time"]
    result = result.assign_coords(time=("time", normalized))
    result["time"].attrs.update(original_time.attrs)
    result["time"].attrs.update(
        {
            "normalized_from": "time_bounds",
            "interval_position": position,
        }
    )
    result.attrs.update(
        {
            "history_time_normalized": "true",
            "history_time_source": "time_bounds",
            "history_time_position": position,
        }
    )
    if result is not dataset:
        result.set_close(dataset.close)
    return result

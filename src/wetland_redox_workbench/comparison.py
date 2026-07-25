"""Utilities for preparing model-observation comparisons.

These functions perform explicit unit conversion, model aggregation, timestamp
alignment, and diagnostic summaries. They are independent of file discovery,
site-specific variable choices, model execution, BOA objectives, and plotting.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
import xarray as xr


AggregationMethod = Literal["mean", "sum", "min", "max", "median"]


def apply_linear_conversion(
    values: pd.Series,
    *,
    scale: float,
    offset: float = 0.0,
    target_units: str | None = None,
    name: str | None = None,
) -> pd.Series:
    """Apply a linear unit or sign conversion to a numeric series.

    Each value is converted using ``value * scale + offset``. Missing values
    remain missing, the input series is not modified, and the conversion is
    recorded in the returned series metadata.

    Parameters
    ----------
    values
        Numeric values to convert.
    scale
        Finite multiplier applied to each value.
    offset
        Finite value added after scaling.
    target_units
        Units assigned to the returned series. When omitted, retain the input
        units.
    name
        Name assigned to the returned series. When omitted, retain the input
        name.

    Returns
    -------
    pandas.Series
        Converted values with the input metadata and an appended
        ``conversion_history`` record.
    """
    if not pd.api.types.is_numeric_dtype(values.dtype):
        raise TypeError("Values to convert must be numeric")
    if not np.isfinite(scale) or not np.isfinite(offset):
        raise ValueError("Conversion scale and offset must be finite")

    converted = values.astype(float) * scale + offset
    converted.name = name if name is not None else values.name
    converted.attrs.update(values.attrs)

    history = list(values.attrs.get("conversion_history", []))
    history.append(
        {
            "scale": scale,
            "offset": offset,
            "source_units": values.attrs.get("units"),
            "target_units": target_units,
        }
    )
    converted.attrs["conversion_history"] = history
    if target_units is not None:
        converted.attrs["units"] = target_units
    return converted


def aggregate_model_timeseries(
    model: xr.DataArray,
    *,
    frequency: str = "1D",
    method: AggregationMethod = "mean",
    skipna: bool = False,
) -> xr.DataArray:
    """Aggregate a scalar ELM time series to a comparison frequency.

    The input must already have an exact, intentional time coordinate, normally
    produced by :func:`~wetland_redox_workbench.elm_output.normalize_history_time`
    and :func:`~wetland_redox_workbench.elm_output.scalar_timeseries`. This
    function does not choose an interval start, midpoint, or end.

    Parameters
    ----------
    model
        One-dimensional model values with a unique, increasing time index.
    frequency
        Xarray-compatible frequency defining the aggregation periods.
    method
        Aggregation operation: ``"mean"``, ``"sum"``, ``"min"``, ``"max"``,
        or ``"median"``.
    skipna
        Whether to ignore missing model values within an aggregation period.
        The default is strict so missing model output is not hidden.

    Returns
    -------
    xarray.DataArray
        Calendar-aware aggregated values retaining the input metadata and an
        appended ``aggregation_history`` record.
    """
    if model.dims != ("time",):
        raise ValueError(
            "Model data must be a one-dimensional time series; "
            f"found dimensions {model.dims}"
        )
    if model.sizes["time"] == 0:
        raise ValueError("Model time series is empty")
    time_index = model.indexes.get("time")
    if time_index is None:
        raise ValueError("Model data has no indexed time coordinate")
    if time_index.has_duplicates:
        raise ValueError("Model timestamps must be unique")
    if not time_index.is_monotonic_increasing:
        raise ValueError("Model timestamps must be sorted in increasing order")

    grouped = model.resample(time=frequency)
    if method == "mean":
        aggregated = grouped.mean(skipna=skipna)
    elif method == "sum":
        aggregated = grouped.sum(skipna=skipna, min_count=1)
    elif method == "min":
        aggregated = grouped.min(skipna=skipna)
    elif method == "max":
        aggregated = grouped.max(skipna=skipna)
    elif method == "median":
        aggregated = grouped.median(skipna=skipna)
    else:
        raise ValueError(f"Unsupported aggregation method: {method!r}")

    if aggregated.sizes.get("time", 0) == 0:
        raise ValueError("Model aggregation produced no time periods")
    history = list(model.attrs.get("aggregation_history", []))
    history.append({"frequency": frequency, "method": method, "skipna": skipna})
    aggregated.attrs.update(model.attrs)
    aggregated.attrs["aggregation_history"] = history
    return aggregated


def align_model_observations(
    model: xr.DataArray | pd.Series,
    observations: pd.Series,
    *,
    drop_missing: bool = True,
    min_pairs: int = 1,
) -> pd.DataFrame:
    """Align model and observation values on calendar timestamps.

    Alignment uses an inner timestamp join rather than record position. ELM
    no-leap ``cftime`` timestamps are converted to timezone-naive pandas
    timestamps using xarray's ``CFTimeIndex`` conversion. Duplicate timestamps,
    unsupported calendar dates, and insufficient valid overlap raise errors.

    Parameters
    ----------
    model
        One-dimensional model values indexed by time.
    observations
        Numeric observation values with a timezone-naive
        :class:`pandas.DatetimeIndex`.
    drop_missing
        Remove rows where either value is missing. When false, retain those
        rows but count only complete pairs toward ``min_pairs``.
    min_pairs
        Minimum number of valid overlapping model-observation pairs.

    Returns
    -------
    pandas.DataFrame
        Time-indexed table with ``model`` and ``observation`` columns.
    """
    if min_pairs < 1:
        raise ValueError("min_pairs must be at least 1")

    model_series = _model_to_series(model)
    observation_series = _require_datetime_series(observations, "Observation")
    model_series = _require_numeric_series(model_series, "Model")
    observation_series = _require_numeric_series(observation_series, "Observation")

    comparison = pd.concat(
        [model_series.rename("model"), observation_series.rename("observation")],
        axis="columns",
        join="inner",
    ).sort_index()
    if drop_missing:
        comparison = comparison.dropna(subset=["model", "observation"])

    paired_count = int(comparison[["model", "observation"]].notna().all(axis=1).sum())
    if paired_count < min_pairs:
        raise ValueError(
            f"Model and observations have {paired_count} valid overlapping pair(s); "
            f"at least {min_pairs} required"
        )
    comparison.attrs.update(
        {
            "drop_missing": drop_missing,
            "minimum_pairs": min_pairs,
            "paired_count": paired_count,
        }
    )
    return comparison


def summarize_comparison(comparison: pd.DataFrame) -> pd.Series:
    """Summarize an aligned model-observation comparison.

    Parameters
    ----------
    comparison
        Time-indexed table containing numeric ``model`` and ``observation``
        columns. Rows missing either value are excluded from the summary.

    Returns
    -------
    pandas.Series
        Paired count, time range, model and observation means and ranges, bias,
        mean absolute error, RMSE, and correlation. Correlation is missing when
        fewer than two pairs are available or either series is constant.
    """
    required = ["model", "observation"]
    missing = [column for column in required if column not in comparison]
    if missing:
        raise KeyError(f"Comparison table is missing columns: {missing}")
    _require_datetime_index(comparison.index, "Comparison")

    pairs = comparison[required].dropna()
    if pairs.empty:
        raise ValueError("Comparison table contains no valid model-observation pairs")
    model = _require_numeric_series(pairs["model"], "Model")
    observations = _require_numeric_series(pairs["observation"], "Observation")
    difference = model - observations

    correlation = float("nan")
    if len(pairs) >= 2 and model.nunique() > 1 and observations.nunique() > 1:
        correlation = float(model.corr(observations))

    summary = pd.Series(
        {
            "paired_count": int(len(pairs)),
            "start_time": pairs.index.min(),
            "end_time": pairs.index.max(),
            "model_mean": float(model.mean()),
            "model_min": float(model.min()),
            "model_max": float(model.max()),
            "observation_mean": float(observations.mean()),
            "observation_min": float(observations.min()),
            "observation_max": float(observations.max()),
            "bias": float(difference.mean()),
            "mean_absolute_error": float(difference.abs().mean()),
            "rmse": float(np.sqrt(np.mean(np.square(difference)))),
            "correlation": correlation,
        },
        name="comparison_summary",
    )
    summary.attrs.update(comparison.attrs)
    return summary


def _model_to_series(model: xr.DataArray | pd.Series) -> pd.Series:
    """Return one-dimensional model values as a validated pandas series."""
    if isinstance(model, pd.Series):
        return _require_datetime_series(model, "Model")
    if not isinstance(model, xr.DataArray):
        raise TypeError("Model values must be an xarray DataArray or pandas Series")
    if model.dims != ("time",):
        raise ValueError(
            "Model data must be a one-dimensional time series; "
            f"found dimensions {model.dims}"
        )

    time_index = model.indexes.get("time")
    if time_index is None:
        raise ValueError("Model data has no indexed time coordinate")

    series = model.to_series()
    if isinstance(time_index, xr.CFTimeIndex):
        series.index = time_index.to_datetimeindex(
            unsafe=True,
            time_unit="ns",
        )
    series.attrs.update(model.attrs)
    return _require_datetime_series(series, "Model")


def _require_datetime_series(series: pd.Series, label: str) -> pd.Series:
    """Validate a datetime-indexed series and return it in timestamp order."""
    _require_datetime_index(series.index, label)
    if series.index.has_duplicates:
        raise ValueError(f"{label} timestamps must be unique")
    return series.sort_index()


def _require_datetime_index(index: pd.Index, label: str) -> None:
    """Require a timezone-naive pandas datetime index."""
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"{label} values must use a pandas DatetimeIndex")
    if index.tz is not None:
        raise ValueError(f"{label} timestamps must be timezone-naive")


def _require_numeric_series(series: pd.Series, label: str) -> pd.Series:
    """Require numeric series values."""
    if not pd.api.types.is_numeric_dtype(series.dtype):
        raise TypeError(f"{label} values must be numeric")
    return series

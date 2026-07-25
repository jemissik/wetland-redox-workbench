"""Utilities for loading, selecting, and aggregating observation data.

These functions provide reusable handling for time-indexed observation tables,
including timestamp validation, missing-value treatment, calendar selection,
coverage diagnostics, and aggregation. They are independent of ELM variables,
model-output paths, unit conversions, BOA metrics, and plotting.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import pandas as pd


PathLike = str | Path
AggregationMethod = Literal["mean", "sum", "min", "max", "median"]


def load_observations(
    path: PathLike,
    *,
    time_column: str,
    columns: Sequence[str] | None = None,
    datetime_format: str | None = None,
    missing_values: Sequence[float | int | str] = (-9999,),
) -> pd.DataFrame:
    """Load selected observations from a CSV file with a datetime index.

    The timestamp column is parsed, validated, and moved to a sorted
    :class:`pandas.DatetimeIndex`. Missing or unparseable timestamps and
    duplicate timestamps raise errors. Configured missing data values and pandas'
    standard missing-value strings are represented as missing data. The source
    file is read-only and is not modified.

    Parameters
    ----------
    path
        Path to the observation CSV file.
    time_column
        Name of the column containing observation timestamps.
    columns
        Data columns to load. When omitted, load every column other than the
        timestamp column.
    datetime_format
        Optional explicit format passed to :func:`pandas.to_datetime`.
    missing_values
        Additional values that should be treated as missing.

    Returns
    -------
    pandas.DataFrame
        Observation values indexed by unique, sorted timestamps. The dataframe
        metadata records the source path, timestamp column, datetime format,
        and configured missing values.

    Notes
    -----
    This function does not perform unit conversion, sign conversion,
    aggregation, or model alignment.
    """
    path = Path(path)
    requested_columns = list(columns) if columns is not None else None
    usecols = None
    if requested_columns is not None:
        usecols = list(dict.fromkeys([time_column, *requested_columns]))

    observations = pd.read_csv(
        path,
        usecols=usecols,
        na_values=list(missing_values),
        keep_default_na=True,
    )
    if time_column not in observations:
        raise KeyError(f"Timestamp column {time_column!r} is not present in {path}")

    raw_time = observations.pop(time_column)
    try:
        parsed_time = pd.to_datetime(
            raw_time.astype("string"),
            format=datetime_format,
            errors="raise",
        )
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Could not parse observation timestamps from column {time_column!r} "
            f"in {path}"
        ) from error

    if parsed_time.isna().any():
        invalid_count = int(parsed_time.isna().sum())
        raise ValueError(
            f"Timestamp column {time_column!r} contains {invalid_count} missing value(s)"
        )

    observations.index = pd.DatetimeIndex(parsed_time, name=time_column)
    if observations.index.has_duplicates:
        duplicate_times = observations.index[observations.index.duplicated()].unique()
        examples = ", ".join(str(value) for value in duplicate_times[:3])
        raise ValueError(
            f"Observation timestamps contain {len(duplicate_times)} duplicate value(s); "
            f"examples: {examples}"
        )

    observations = observations.sort_index()
    observations.attrs.update(
        {
            "source_path": str(path),
            "time_column": time_column,
            "datetime_format": datetime_format,
            "missing_values": tuple(missing_values),
        }
    )
    return observations


def select_observation_period(
    observations: pd.DataFrame,
    *,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    drop_february_29: bool = True,
) -> pd.DataFrame:
    """Return observations restricted to a requested calendar period.

    February 29 is dropped by default for comparison with ELM's no-leap
    calendar. Pass ``drop_february_29=False`` to retain it for observation-only
    analyses.
    """
    _require_datetime_index(observations)
    selected = observations.sort_index().loc[start:end].copy()
    if drop_february_29:
        index = selected.index
        selected = selected.loc[~((index.month == 2) & (index.day == 29))].copy()
    selected.attrs.update(observations.attrs)
    selected.attrs.update(
        {
            "period_start": str(start) if start is not None else None,
            "period_end": str(end) if end is not None else None,
            "february_29_dropped": drop_february_29,
        }
    )
    return selected


def observation_coverage(
    observations: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    frequency: str = "1D",
    expected_interval: str | pd.Timedelta | None = None,
) -> pd.DataFrame:
    """Summarize valid observation coverage for each aggregation period.

    This diagnostic reports missing-data coverage without aggregating,
    filtering, or otherwise modifying the observation values. The returned
    table has one row per period and variable, with the valid count, expected
    count, coverage fraction, first and last valid timestamps, and whether the
    period has the expected number of valid records.

    Parameters
    ----------
    observations
        Observation values with a unique :class:`pandas.DatetimeIndex`.
    columns
        Numeric variables to summarize. When omitted, summarize all numeric
        columns.
    frequency
        Pandas-compatible frequency defining the periods to summarize.
    expected_interval
        Expected spacing between observations. When omitted, expected counts,
        coverage fractions, and completeness are left unavailable rather than
        inferred.

    Returns
    -------
    pandas.DataFrame
        Tidy coverage table with one row per period and variable.

    Notes
    -----
    Completeness is based on record counts. It does not verify that records are
    evenly spaced or that a period contains no interior gaps.
    """
    _require_datetime_index(observations)
    selected = _select_numeric_columns(observations, columns)
    expected_count = _expected_count(frequency, expected_interval)
    rows: list[pd.DataFrame] = []

    for column in selected:
        grouped = selected[column].resample(frequency)
        valid_count = grouped.count().astype("int64")
        first_valid = grouped.apply(
            lambda values: values.first_valid_index() if values.notna().any() else pd.NaT
        )
        last_valid = grouped.apply(
            lambda values: values.last_valid_index() if values.notna().any() else pd.NaT
        )
        summary = pd.DataFrame(
            {
                "period": valid_count.index,
                "variable": column,
                "valid_count": valid_count.to_numpy(),
                "first_valid_time": first_valid.to_numpy(),
                "last_valid_time": last_valid.to_numpy(),
            }
        )
        if expected_count is None:
            summary["expected_count"] = pd.array(
                [pd.NA] * len(summary), dtype="Int64"
            )
            summary["coverage_fraction"] = float("nan")
            summary["complete"] = pd.array(
                [pd.NA] * len(summary), dtype="boolean"
            )
        else:
            summary["expected_count"] = expected_count
            summary["coverage_fraction"] = summary["valid_count"] / expected_count
            summary["complete"] = summary["valid_count"] >= expected_count
        rows.append(summary)

    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=[
            "period",
            "variable",
            "valid_count",
            "expected_count",
            "coverage_fraction",
            "complete",
            "first_valid_time",
            "last_valid_time",
        ]
    )
    result.attrs.update(observations.attrs)
    result.attrs.update(
        {
            "coverage_frequency": frequency,
            "expected_interval": (
                str(expected_interval) if expected_interval is not None else None
            ),
        }
    )
    return result


def aggregate_observations(
    observations: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    frequency: str,
    method: AggregationMethod = "mean",
    min_count: int | None = None,
    min_coverage: float | None = None,
    expected_interval: str | pd.Timedelta | None = None,
    label: Literal["left", "right"] = "left",
    closed: Literal["left", "right"] = "left",
) -> pd.DataFrame:
    """Resample numeric observations with explicit completeness rules.

    Values are aggregated into periods defined by ``frequency``. An aggregate
    is replaced with missing data when it fails either the requested minimum
    valid count or minimum coverage fraction. The input dataframe is not
    modified.

    Parameters
    ----------
    observations
        Observation values with a unique :class:`pandas.DatetimeIndex`.
    columns
        Numeric variables to aggregate. When omitted, aggregate all numeric
        columns.
    frequency
        Pandas-compatible frequency defining the aggregation periods.
    method
        Aggregation operation: ``"mean"``, ``"sum"``, ``"min"``, ``"max"``,
        or ``"median"``.
    min_count
        Minimum number of valid observations required in each period.
    min_coverage
        Minimum fraction of expected observations required in each period.
        ``expected_interval`` is required when this option is set.
    expected_interval
        Expected spacing between observations, used with ``frequency`` to
        calculate the expected number of records per period.
    label
        Whether each resulting period is labeled by its left or right boundary.
    closed
        Whether each period includes its left or right boundary.

    Returns
    -------
    pandas.DataFrame
        Aggregated values with failed periods masked as missing. Dataframe
        metadata retain the input metadata and record each aggregation step in
        ``aggregation_history``.

    Notes
    -----
    Call this function repeatedly for multi-stage aggregation. Use
    :func:`observation_coverage` when a separate tidy coverage table is needed.
    This function does not perform unit conversion, sign conversion, or model
    alignment.
    """
    _require_datetime_index(observations)
    if min_count is not None and min_count < 1:
        raise ValueError("min_count must be at least 1")
    if min_coverage is not None and not 0 <= min_coverage <= 1:
        raise ValueError("min_coverage must be between 0 and 1")
    if min_coverage is not None and expected_interval is None:
        raise ValueError("expected_interval is required when min_coverage is set")

    selected = _select_numeric_columns(observations, columns)
    grouped = selected.resample(frequency, label=label, closed=closed)
    if method == "mean":
        aggregated = grouped.mean()
    elif method == "sum":
        aggregated = grouped.sum(min_count=1)
    elif method == "min":
        aggregated = grouped.min()
    elif method == "max":
        aggregated = grouped.max()
    elif method == "median":
        aggregated = grouped.median()
    else:  # Defensive guard for untyped callers.
        raise ValueError(f"Unsupported aggregation method: {method!r}")

    valid_counts = grouped.count()
    valid = pd.DataFrame(True, index=aggregated.index, columns=aggregated.columns)
    if min_count is not None:
        valid &= valid_counts >= min_count
    if min_coverage is not None:
        expected_count = _expected_count(frequency, expected_interval)
        if expected_count is None:  # Kept explicit for static type checkers.
            raise ValueError("Could not determine expected observation count")
        valid &= valid_counts / expected_count >= min_coverage
    aggregated = aggregated.where(valid)

    history = list(observations.attrs.get("aggregation_history", []))
    history.append(
        {
            "frequency": frequency,
            "method": method,
            "min_count": min_count,
            "min_coverage": min_coverage,
            "expected_interval": (
                str(expected_interval) if expected_interval is not None else None
            ),
            "label": label,
            "closed": closed,
        }
    )
    aggregated.attrs.update(observations.attrs)
    aggregated.attrs["aggregation_history"] = history
    return aggregated


def _require_datetime_index(observations: pd.DataFrame) -> None:
    if not isinstance(observations.index, pd.DatetimeIndex):
        raise TypeError("Observations must use a pandas DatetimeIndex")
    if observations.index.has_duplicates:
        raise ValueError("Observation timestamps must be unique")


def _select_numeric_columns(
    observations: pd.DataFrame,
    columns: Sequence[str] | None,
) -> pd.DataFrame:
    if columns is None:
        selected = observations.select_dtypes(include="number")
        if selected.shape[1] == 0:
            raise ValueError("Observation table contains no numeric columns")
        return selected

    names = list(columns)
    missing = [name for name in names if name not in observations]
    if missing:
        raise KeyError(f"Observation table is missing columns: {missing}")
    nonnumeric = [
        name for name in names if not pd.api.types.is_numeric_dtype(observations[name])
    ]
    if nonnumeric:
        raise TypeError(f"Observation columns are not numeric: {nonnumeric}")
    return observations[names]


def _expected_count(
    frequency: str,
    expected_interval: str | pd.Timedelta | None,
) -> int | None:
    if expected_interval is None:
        return None
    try:
        period = pd.Timedelta(frequency)
    except ValueError as error:
        raise ValueError(
            "Coverage calculations currently require a fixed aggregation frequency"
        ) from error
    interval = pd.Timedelta(expected_interval)
    if period <= pd.Timedelta(0) or interval <= pd.Timedelta(0):
        raise ValueError("frequency and expected_interval must be positive")
    quotient, remainder = divmod(period.value, interval.value)
    if remainder:
        raise ValueError(
            f"Aggregation frequency {frequency!r} is not evenly divisible by "
            f"expected interval {str(expected_interval)!r}"
        )
    return int(quotient)

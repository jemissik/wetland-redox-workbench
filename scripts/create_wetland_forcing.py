#!/usr/bin/env python3
"""Create a wetland boundary-forcing NetCDF from a CSV file.

The CSV must contain a timestamp column and a regular water-level column.
Optional columns can supply salinity and the model's reactive DOM1 pool. The
output uses a regular no-leap time axis and includes ELM-style `start_year` /
`end_year` indexing metadata.

Example:

    python create_wetland_forcing.py \
      --csv water_level.csv \
      --time-column time \
      --water-level-column water_level \
      --water-level-units m \
      --site-name US-LA2 \
      --lat 29.8587 \
      --lon 269.7131 \
      --output wetland_boundary_forcing_US_LA2_waterlevel.nc

Optional salinity and DOM1:

    python create_wetland_forcing.py \
      --csv wetland_boundary.csv \
      --time-column time \
      --water-level-column water_level_m \
      --salinity-column salinity_ppt \
      --dom1-column doc_mg_c_l \
      --dom1-units mg-C/L \
      --site-name EXAMPLE \
      --lat 29.0 \
      --lon -90.0 \
      --output wetland_boundary_forcing_EXAMPLE.nc
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import netCDF4 as nc
import numpy as np
import pandas as pd


MONTH_LENGTHS_NOLEAP = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
MONTH_STARTS_NOLEAP = np.concatenate(([0], np.cumsum(MONTH_LENGTHS_NOLEAP[:-1])))
CARBON_MOLAR_MASS_G_PER_MOL = 12.011


def write_site_name(ds: nc.Dataset, site_name: str, nchar: int) -> None:
    value = np.full((1, nchar), b" ", dtype="S1")
    encoded = site_name.encode("ascii")
    value[0, : min(len(encoded), nchar)] = np.frombuffer(encoded[:nchar], dtype="S1")
    ds.variables["site_name"][:] = value


def convert_water_level(values: np.ndarray, units: str) -> np.ndarray:
    units_norm = units.lower()
    if units_norm in {"m", "meter", "meters"}:
        return values.astype(np.float64)
    if units_norm in {"mm", "millimeter", "millimeters"}:
        return values.astype(np.float64) / 1000.0
    raise ValueError(f"Unsupported water-level units {units!r}; use 'm' or 'mm'")


def convert_salinity(values: np.ndarray, units: str) -> np.ndarray:
    """Convert supported salinity units to the model's ppt convention."""
    if units.lower() == "ppt":
        return values.astype(np.float64)
    raise ValueError(f"Unsupported salinity units {units!r}; use 'ppt'")


def convert_dom1(values: np.ndarray, units: str) -> np.ndarray:
    """Convert DOM1 or DOC-carbon values to mol DOM1 per m3 H2O."""
    if units in {"mol/m3", "mmol/L"}:
        return values.astype(np.float64)
    if units in {"mg-C/L", "g-C/m3"}:
        return values.astype(np.float64) / CARBON_MOLAR_MASS_G_PER_MOL
    raise ValueError(
        f"Unsupported DOM1 units {units!r}; use 'mol/m3', 'mmol/L', "
        "'mg-C/L', or 'g-C/m3'"
    )


def validate_values(
    values: np.ndarray,
    *,
    name: str,
    nonnegative: bool,
) -> None:
    """Reject missing, infinite, and optionally negative forcing values."""
    if not np.isfinite(values).all():
        raise ValueError(
            f"{name} contains missing or non-finite values; gap-fill before "
            "creating the forcing file"
        )
    if nonnegative and np.any(values < 0.0):
        raise ValueError(f"{name} must be non-negative")


def is_leap_day(times: pd.Series) -> pd.Series:
    return (times.dt.month == 2) & (times.dt.day == 29)


def noleap_day_of_year(timestamp: pd.Timestamp) -> int:
    return int(MONTH_STARTS_NOLEAP[timestamp.month - 1] + timestamp.day)


def expected_noleap_dates(start_year: int, end_year: int) -> pd.DatetimeIndex:
    dates = []
    for year in range(start_year, end_year + 1):
        for month, month_length in enumerate(MONTH_LENGTHS_NOLEAP, start=1):
            for day in range(1, month_length + 1):
                dates.append(pd.Timestamp(year=year, month=month, day=day))
    return pd.DatetimeIndex(dates)


def expected_noleap_times(
    start_year: int,
    end_year: int,
    records_per_day: int,
) -> pd.DatetimeIndex:
    freq = pd.to_timedelta(86400 // records_per_day, unit="s")
    times = []
    for date in expected_noleap_dates(start_year, end_year):
        for record in range(records_per_day):
            times.append(date + record * freq)
    return pd.DatetimeIndex(times)


def format_time_examples(dates: pd.DatetimeIndex, limit: int = 5) -> str:
    if len(dates) == 0:
        return "none"
    values = [str(date) for date in dates[:limit]]
    if len(dates) > limit:
        values.append("...")
    return ", ".join(values)


def parse_time_resolution_days(value: str) -> float:
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    return float(value)


def prepare_regular_noleap_series(
    csv_file: Path,
    time_column: str,
    water_level_column: str,
    water_level_units: str,
    start_year_arg: Optional[int],
    end_year_arg: Optional[int],
    keep_leap_days: bool,
    time_resolution_days: float,
    salinity_column: Optional[str] = None,
    salinity_units: str = "ppt",
    dom1_column: Optional[str] = None,
    dom1_units: str = "mol/m3",
) -> tuple[pd.DatetimeIndex, dict[str, np.ndarray], int, int, int]:
    if time_resolution_days <= 0.0 or time_resolution_days > 1.0:
        raise ValueError("time_resolution_days must be > 0 and <= 1")
    records_per_day = round(1.0 / time_resolution_days)
    if abs(time_resolution_days * records_per_day - 1.0) > 1.0e-8:
        raise ValueError("time_resolution_days must divide evenly into one day")
    seconds_per_record = 86400 / records_per_day
    if abs(round(seconds_per_record) - seconds_per_record) > 1.0e-8:
        raise ValueError(
            "time_resolution_days must correspond to an integer number of seconds"
        )

    df = pd.read_csv(csv_file)
    if time_column not in df:
        raise KeyError(f"CSV is missing time column {time_column!r}")
    if water_level_column not in df:
        raise KeyError(f"CSV is missing water-level column {water_level_column!r}")
    if salinity_column is not None and salinity_column not in df:
        raise KeyError(f"CSV is missing salinity column {salinity_column!r}")
    if dom1_column is not None and dom1_column not in df:
        raise KeyError(f"CSV is missing DOM1 column {dom1_column!r}")

    times = pd.to_datetime(df[time_column])
    if times.isna().any():
        raise ValueError("Could not parse all timestamps")

    forcing_values = {
        "water_level": convert_water_level(
            df[water_level_column].to_numpy(dtype=np.float64),
            water_level_units,
        )
    }
    validate_values(
        forcing_values["water_level"],
        name="water_level",
        nonnegative=False,
    )

    if salinity_column is not None:
        forcing_values["bc_salinity"] = convert_salinity(
            df[salinity_column].to_numpy(dtype=np.float64),
            salinity_units,
        )
        validate_values(
            forcing_values["bc_salinity"],
            name="bc_salinity",
            nonnegative=True,
        )

    if dom1_column is not None:
        forcing_values["bc_DOM1"] = convert_dom1(
            df[dom1_column].to_numpy(dtype=np.float64),
            dom1_units,
        )
        validate_values(
            forcing_values["bc_DOM1"],
            name="bc_DOM1",
            nonnegative=True,
        )

    work = pd.DataFrame({"time": times, **forcing_values})
    if not keep_leap_days:
        work = work.loc[~is_leap_day(work["time"])].copy()

    work["time"] = work["time"].dt.round(f"{int(round(seconds_per_record))}s")
    if work["time"].duplicated().any():
        duplicated = pd.DatetimeIndex(
            work.loc[work["time"].duplicated(), "time"].unique()
        )
        raise ValueError(
            "CSV has more than one record for at least one forcing time after timestamp rounding: "
            f"{format_time_examples(duplicated)}"
        )

    if work.empty:
        raise ValueError("No records remain after timestamp filtering")

    start_year = (
        start_year_arg
        if start_year_arg is not None
        else int(work["time"].dt.year.min())
    )
    end_year = (
        end_year_arg if end_year_arg is not None else int(work["time"].dt.year.max())
    )
    if end_year < start_year:
        raise ValueError("end_year must be >= start_year")

    work = work.loc[
        (work["time"].dt.year >= start_year) & (work["time"].dt.year <= end_year)
    ].copy()
    expected = expected_noleap_times(start_year, end_year, records_per_day)
    actual = pd.DatetimeIndex(work["time"])
    missing = expected.difference(actual)
    extra = actual.difference(expected)
    if len(missing) > 0 or len(extra) > 0:
        raise ValueError(
            "CSV does not form a complete regular no-leap forcing period. "
            f"Missing: {format_time_examples(missing)}; extra: {format_time_examples(extra)}"
        )

    work = work.set_index("time").loc[expected]
    prepared_values = {
        name: work[name].to_numpy(dtype=np.float64) for name in forcing_values
    }
    return expected, prepared_values, start_year, end_year, records_per_day


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--time-column", default="time")
    parser.add_argument("--water-level-column", default="water_level")
    parser.add_argument("--water-level-units", default="m", choices=["m", "mm"])
    parser.add_argument(
        "--salinity-column",
        default=None,
        help="Optional CSV column containing wetland boundary salinity.",
    )
    parser.add_argument(
        "--salinity-units",
        default="ppt",
        choices=["ppt"],
        help="Units of --salinity-column; the current model interface expects ppt.",
    )
    parser.add_argument(
        "--dom1-column",
        default=None,
        help=(
            "Optional CSV column mapped to the model's reactive DOM1 pool. "
            "A measured DOC column may be used only when representing all of "
            "that DOC as DOM1 is an appropriate modeling assumption."
        ),
    )
    parser.add_argument(
        "--dom1-units",
        default="mol/m3",
        choices=["mol/m3", "mmol/L", "mg-C/L", "g-C/m3"],
        help=(
            "Units of --dom1-column. Carbon-mass units are converted assuming "
            "one mole of carbon per mole of DOM1."
        ),
    )
    parser.add_argument("--site-name", required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--start-year", type=int, default=None)
    parser.add_argument("--end-year", type=int, default=None)
    parser.add_argument(
        "--time-resolution-days",
        default="1.0",
        help="Forcing interval in days. Use 1.0 for daily, 1/24 for hourly, or 1/48 for half-hourly.",
    )
    parser.add_argument("--calendar", default="noleap", choices=["noleap"])
    parser.add_argument(
        "--keep-leap-days",
        action="store_true",
        help="Do not drop Feb. 29 before validation. This is mostly for debugging; ELM forcing must be noleap.",
    )
    args = parser.parse_args()

    time_resolution_days = parse_time_resolution_days(args.time_resolution_days)
    (
        dates,
        forcing_values,
        start_year,
        end_year,
        records_per_day,
    ) = prepare_regular_noleap_series(
        csv_file=args.csv,
        time_column=args.time_column,
        water_level_column=args.water_level_column,
        water_level_units=args.water_level_units,
        start_year_arg=args.start_year,
        end_year_arg=args.end_year,
        keep_leap_days=args.keep_leap_days,
        time_resolution_days=time_resolution_days,
        salinity_column=args.salinity_column,
        salinity_units=args.salinity_units,
        dom1_column=args.dom1_column,
        dom1_units=args.dom1_units,
    )

    ntime = len(dates)
    nchar = 64
    time_days = np.arange(ntime, dtype=np.float64) * time_resolution_days
    source_year = np.asarray([date.year for date in dates], dtype=np.int32)
    day_of_year = np.asarray(
        [noleap_day_of_year(date) for date in dates], dtype=np.int32
    )
    record_of_day = np.asarray(
        [
            int(
                (date.hour * 3600 + date.minute * 60 + date.second)
                / (86400 / records_per_day)
            )
            + 1
            for date in dates
        ],
        dtype=np.int32,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with nc.Dataset(args.output, "w", format="NETCDF4_CLASSIC") as dst:
        dst.createDimension("time", ntime)
        dst.createDimension("gridcell", 1)
        dst.createDimension("scalar", 1)
        dst.createDimension("nchar", nchar)

        time = dst.createVariable("time", "f8", ("time",))
        time.long_name = "time"
        time.units = f"days since {start_year}-01-01 00:00:00"
        time.calendar = args.calendar
        time[:] = time_days

        start = dst.createVariable("start_year", "i4", ("scalar",))
        start.long_name = "first forcing year"
        start.units = "year"
        start[:] = [start_year]

        end = dst.createVariable("end_year", "i4", ("scalar",))
        end.long_name = "last forcing year"
        end.units = "year"
        end[:] = [end_year]

        tres = dst.createVariable("time_resolution_days", "f8", ("scalar",))
        tres.long_name = "forcing time resolution"
        tres.units = "days"
        tres[:] = [time_resolution_days]

        gridcell = dst.createVariable("gridcell", "i4", ("gridcell",))
        gridcell.long_name = "forcing file gridcell index"
        gridcell.units = "1"
        gridcell[:] = [1]

        lat = dst.createVariable("lat", "f8", ("gridcell",))
        lat.long_name = "latitude"
        lat.units = "degrees_north"
        lat[:] = [args.lat]

        lon = dst.createVariable("lon", "f8", ("gridcell",))
        lon.long_name = "longitude"
        lon.units = "degrees_east"
        lon[:] = [args.lon]

        dst.createVariable("site_name", "S1", ("gridcell", "nchar"))
        dst.variables["site_name"].long_name = "site name"
        write_site_name(dst, args.site_name, nchar)

        year_var = dst.createVariable("source_year", "i4", ("time",))
        year_var.long_name = "source calendar year"
        year_var.units = "year"
        year_var[:] = source_year

        doy_var = dst.createVariable("day_of_year", "i4", ("time",))
        doy_var.long_name = "source no-leap day of year"
        doy_var.units = "day"
        doy_var[:] = day_of_year

        record_var = dst.createVariable("record_of_day", "i4", ("time",))
        record_var.long_name = "forcing record within no-leap day"
        record_var.units = "1"
        record_var[:] = record_of_day

        water = dst.createVariable(
            "water_level", "f8", ("time", "gridcell"), fill_value=np.nan
        )
        water.long_name = "observed wetland water level relative to soil surface"
        water.units = "m"
        water.positive = "up"
        water.reference = "soil surface"
        water.source_units = args.water_level_units
        water.source_column = args.water_level_column
        water[:, 0] = forcing_values["water_level"]

        if args.salinity_column is not None:
            salinity = dst.createVariable(
                "bc_salinity",
                "f8",
                ("time", "gridcell"),
                fill_value=np.nan,
            )
            salinity.long_name = "wetland boundary salinity concentration"
            salinity.units = "ppt"
            salinity.source_units = args.salinity_units
            salinity.source_column = args.salinity_column
            salinity[:, 0] = forcing_values["bc_salinity"]

        if args.dom1_column is not None:
            dom1 = dst.createVariable(
                "bc_DOM1",
                "f8",
                ("time", "gridcell"),
                fill_value=np.nan,
            )
            dom1.long_name = "wetland boundary DOM1 concentration"
            dom1.units = "mol/m3 H2O"
            dom1.source_units = args.dom1_units
            dom1.source_column = args.dom1_column
            dom1.mapping_note = (
                "The input is represented entirely as the reactive PFLOTRAN/Alquimia "
                "DOM1 species, which carries one mole of carbon per mole of DOM1. "
                "This mapping also inherits the DOM1 C:N and reaction properties "
                "defined by the active model configuration."
            )
            dom1[:, 0] = forcing_values["bc_DOM1"]

        dst.title = f"{args.site_name} wetland boundary forcing"
        dst.source_csv = str(args.csv)
        dst.forcing_variables = " ".join(forcing_values)
        dst.forcing_calendar = "noleap"
        dst.forcing_time_convention = (
            "Regular no-leap values are indexed like ELM met forcing: model years within "
            "start_year:end_year align to the matching forcing year; years outside "
            "that range cycle through the available forcing years."
        )
        dst.history = "Created by create_wetland_forcing.py"

    print(f"Wrote {args.output}")
    print(f"  time records: {ntime}")
    print(f"  years: {start_year}-{end_year}")
    print(f"  records per day: {records_per_day}")
    water_level = forcing_values["water_level"]
    print(
        f"  water_level range: {np.min(water_level):.6g} to {np.max(water_level):.6g} m"
    )
    if "bc_salinity" in forcing_values:
        salinity = forcing_values["bc_salinity"]
        print(
            f"  bc_salinity range: {np.min(salinity):.6g} to {np.max(salinity):.6g} ppt"
        )
    if "bc_DOM1" in forcing_values:
        dom1 = forcing_values["bc_DOM1"]
        print(f"  bc_DOM1 range: {np.min(dom1):.6g} to {np.max(dom1):.6g} mol/m3 H2O")


if __name__ == "__main__":
    main()

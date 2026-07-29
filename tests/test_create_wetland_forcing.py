from pathlib import Path
import subprocess
import sys

import netCDF4 as nc
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).parents[1] / "scripts" / "create_wetland_forcing.py"


def write_leap_year_csv(path: Path) -> None:
    dates = pd.date_range("2000-01-01", "2000-12-31", freq="D")
    pd.DataFrame(
        {
            "time": dates,
            "water_level_mm": 100.0,
            "salinity_ppt": 5.0,
            "doc_mg_c_l": 12.011,
        }
    ).to_csv(path, index=False)


def run_converter(csv_path: Path, output_path: Path, *extra_args: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--csv",
            str(csv_path),
            "--output",
            str(output_path),
            "--time-column",
            "time",
            "--water-level-column",
            "water_level_mm",
            "--water-level-units",
            "mm",
            "--site-name",
            "TEST",
            "--lat",
            "29.0",
            "--lon",
            "-90.0",
            *extra_args,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_water_only_output_remains_supported(tmp_path: Path) -> None:
    csv_path = tmp_path / "forcing.csv"
    output_path = tmp_path / "forcing.nc"
    write_leap_year_csv(csv_path)

    run_converter(csv_path, output_path)

    with nc.Dataset(output_path) as dataset:
        assert len(dataset.dimensions["time"]) == 365
        assert "bc_salinity" not in dataset.variables
        assert "bc_DOM1" not in dataset.variables
        np.testing.assert_allclose(dataset.variables["water_level"][:, 0], 0.1)


def test_optional_salinity_and_doc_carbon_are_written_as_model_inputs(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "forcing.csv"
    output_path = tmp_path / "forcing.nc"
    write_leap_year_csv(csv_path)

    run_converter(
        csv_path,
        output_path,
        "--salinity-column",
        "salinity_ppt",
        "--dom1-column",
        "doc_mg_c_l",
        "--dom1-units",
        "mg-C/L",
    )

    with nc.Dataset(output_path) as dataset:
        assert dataset.forcing_variables == "water_level bc_salinity bc_DOM1"
        np.testing.assert_allclose(dataset.variables["bc_salinity"][:, 0], 5.0)
        np.testing.assert_allclose(dataset.variables["bc_DOM1"][:, 0], 1.0)
        assert dataset.variables["bc_salinity"].units == "ppt"
        assert dataset.variables["bc_DOM1"].units == "mol/m3 H2O"
        assert dataset.variables["bc_DOM1"].source_units == "mg-C/L"
        assert "represented entirely as" in dataset.variables["bc_DOM1"].mapping_note

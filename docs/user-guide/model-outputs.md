# Model Outputs

The run directory contains scientific output, restart state, logs, and copies
of the configuration that ELM used for the run. History files are the main
files used for analysis. Restart files preserve model state so a simulation can
continue, while logs and configuration files help verify and reproduce the
run.

## The Run Directory

### History Files

For most analysis, begin with the ELM history files:

```text
<case-name>.elm.h0.<date>.nc
```

These NetCDF files contain time series such as GPP, methane flux, water table
depth, soil chemistry profiles, and reaction rates. These are the files to
analyze and plot.

A point-site ELM-Wet-Redox run with meteorological bypass forcing usually has
ELM history as its main scientific output. Other E3SM configurations may also
produce history files for atmosphere, river routing, ocean, or other
components.

### Restart Files

Restart files preserve the complete internal state needed to continue a
simulation. They are not alternate history files and are not the normal
starting point for results analysis.

| Filename pattern | Contents |
| --- | --- |
| `<case>.elm.r.<date>.nc` | Complete ELM state needed to restart the land model |
| `<case>.elm.rh0.<date>.nc` | State of the `h0` history accumulator, needed to continue history output correctly |
| `<case>.cpl.r.<date>.nc` | Driver/coupler timing, budget, and land-fraction state |
| `rpointer.lnd` | Name of the ELM restart file to read when continuing the run |
| `rpointer.drv` | Name of the driver restart file to read when continuing the run |

The ELM restart file contains hundreds of variables representing vegetation,
soil water, temperature, carbon, nitrogen, phosphorus, methane state, and
numbered Alquimia mobile, immobile, mineral, and auxiliary arrays. These
variables are organized for exact continuation of the model, not as a stable
analysis interface.

Keep the restart files and pointer files from a checkpoint together. Do not
rename an individual restart file without also updating the corresponding
pointer and case configuration. An `.elm.h0.*.nc` history file cannot replace
an ELM restart file.

### Logs And Supporting Files

| Filename | Purpose |
| --- | --- |
| `cpl.log` | Driver/coupler progress, timestamps, timing, and final termination status |
| `lnd.log` | ELM initialization, input paths, history-field setup, timestep messages, and restart writing |
| `e3sm.log.<job-id>` | Standard output and error from the model executable |
| `rof.log` | River-routing messages; often minimal for a point-site run |
| `slurm-<job-id>.out` | Slurm batch output; exact location depends on the launcher |
| `drv_in` | Driver settings such as calendar, start date, stop condition, restart frequency, and component layout |
| `lnd_in` | ELM settings and the exact input paths, parameter files, chemistry deck, forcing files, and requested history fields |
| `mosart_in` | River-routing namelist |
| `*_modelio.nml` | Input, output, log, and parallel-I/O settings for each component |
| `seq_maps.rc` | Coupling and mapping settings between model components |
| `CNP_parameters.nc` | Soil-order parameter input, when copied into the run directory; this is runtime input, not model output |
| `io_perf_summary_*`, `memory.*.log` | I/O and memory-performance diagnostics, not scientific results |

These files are part of the run record. For example, `lnd_in` tells you which
surface file, initial-condition file, ELM parameter file, Alquimia deck, and
wetland boundary forcing file were actually used. Do not assume that the
original setup command is an exact record of the final run configuration.

## Understanding History Output

### File Names, Streams, And File Splitting

An ELM history filename has several parts:

```text
la2_transient.elm.h0.2012-01-01-00000.nc
```

| Part | Meaning |
| --- | --- |
| `la2_transient` | Case name |
| `elm` | E3SM Land Model component |
| `h0` | First configured ELM history stream |
| `2012-01-01-00000` | Timestamp ELM uses to identify the first history record in this file |
| `nc` | NetCDF file format |

`h0` identifies a history **stream**, not an individual file number. A run can
write many `h0` files. All of them contain consecutive portions of the same
configured stream.

ELM history settings are visible in `lnd_in`. In a normal CIME case, set them
in `user_nl_elm` or through the case-generation tools rather than editing a
generated `lnd_in` by hand. An hourly stream can use settings such as:

```fortran
hist_nhtfrq = -1
hist_mfilt = 744
hist_fincl1 = 'GPP', 'CH4FLUX_ALQUIMIA', 'soil_O2', ...
```

- `hist_nhtfrq = -1` requests hourly history records;
- `hist_mfilt = 744` allows 744 records in each `h0` file;
- `hist_fincl1` adds fields to the first history tape. Despite the `1` in the
  namelist option, files from that tape use the suffix `h0`.

After 744 hourly records fill the example file, ELM opens another `h0` file
and continues writing the same fields. The filename date identifies the file's
first record; inspect `time_bounds` for the exact interval covered by that
record. A filename does not imply that the file contains exactly one month or
one year. Restart boundaries and other history settings can also affect where
files are opened or closed.

ELM can also write separately configured history streams named `h1`, `h2`, and
so on. Each stream can have its own variables, output frequency, and number of
records per file. An `h1` file is therefore not a continuation of an `h0` file.

ELM can include a broad default field list, so a history file may contain many
more fields than those shown explicitly in `hist_fincl1`. Higher-frequency
output and large profile field lists can consume substantial storage. Request
the temporal resolution and variables needed for the scientific question.

### Time And Dimensions

ELM-Wet-Redox runs uses a no-leap calendar. There is no February 29
in the model timeline. History files contain:

| Variable | Meaning |
| --- | --- |
| `time` | Timestamp written by ELM for each history record |
| `time_bounds` | Exact beginning and end of the interval represented by each record |
| `mcdate`, `mcsec`, `nstep` | Model date, seconds, and timestep counters |

Most history fields have `cell_methods = "time: mean"`. Their values are means
over the interval in `time_bounds`, not instantaneous measurements at a single
moment.

The floating-point `time` coordinate can decode a few seconds away from an
exact hour. Use `time_bounds` when exact alignment with observations matters.
The workbench's `normalize_history_time()` function can label each interval by
its start, midpoint, or end without modifying the original NetCDF file.

When observations use a beginning-of-interval timestamp such as
`TIMESTAMP_START`, label the corresponding model interval by its start time.
Other datasets may require midpoint or end labeling.

Common ELM history dimensions include:

| Dimension | Meaning |
| --- | --- |
| `time` | History intervals through the simulation |
| `lndgrid` | Output grid cells; a point-site run usually has one |
| `levgrnd` | ELM soil thermal and hydrologic layers |
| `levdcmp` | Soil biogeochemistry and Alquimia decomposition layers |
| `levsoi` | The upper subset of ELM soil layers |
| `levlak` | Lake layers used by ELM's standard land-model infrastructure |

A variable with dimensions `(time, lndgrid)` is one value per time and site. A
variable with dimensions `(time, levdcmp, lndgrid)` is a vertical soil profile
at every time and site. Do not average or select a soil layer until you know
which scientific question the reduction represents.

Static coordinates such as `ZSOI`, `DZSOI`, `WATSAT`, and `HKSAT` may be
written only in the first file of a history sequence. This is normal; later
files can contain the time-varying fields without repeating every static field.

### Variables

ELM history files contain coordinates and time information, site and soil
properties, ecosystem carbon, water and energy variables, vegetation
variables, standard ELM methane variables, and requested ELM-Wet-Redox soil
chemistry and reaction-rate diagnostics.

An `h0` file can contain hundreds of data variables. The exact list depends on
the ELM source version, enabled model features, history-stream configuration,
and requested field list. Do not treat the field list from one run as
universal. Always check a variable's `long_name`, `units`, dimensions, and
`cell_methods` in the file being analyzed.

#### Carbon, Vegetation, And Water

| Variable | Meaning | Units | Dimensions |
| --- | --- | --- | --- |
| `GPP` | Gross primary production | `gC m-2 s-1` | `time, lndgrid` |
| `NPP` | Net primary production | `gC m-2 s-1` | `time, lndgrid` |
| `NEE` | Net ecosystem exchange; positive is a carbon source to the atmosphere | `gC m-2 s-1` | `time, lndgrid` |
| `ER` | Total ecosystem respiration | `gC m-2 s-1` | `time, lndgrid` |
| `HR` | Heterotrophic respiration | `gC m-2 s-1` | `time, lndgrid` |
| `AR` | Autotrophic respiration | `gC m-2 s-1` | `time, lndgrid` |
| `TLAI` | Total projected leaf area index | `1` | `time, lndgrid` |
| `ELAI` | Exposed one-sided leaf area index | `m2 m-2` | `time, lndgrid` |
| `VCMAX25TOP` | Canopy-top Vcmax at 25 C | `umol CO2 m-2 s-1` | `time, lndgrid` |
| `ZWT` | Water table depth | `m` | `time, lndgrid` |
| `H2OSFC` | Surface water depth | `mm` | `time, lndgrid` |
| `H2OSFC_WET` | Wetland surface water depth | `mm` | `time, lndgrid` |
| `H2OSOI` | Volumetric soil water | `mm3 mm-3` | `time, levgrnd, lndgrid` |
| `TSOI` | Soil temperature | `K` | `time, levgrnd, lndgrid` |

#### Coupled Methane Flux And Transport

| Variable | Meaning | Units | Dimensions |
| --- | --- | --- | --- |
| `CH4FLUX_ALQUIMIA` | Total methane flux from the coupled ELM-Alquimia calculation | `gC m-2 s-1` | `time, lndgrid` |
| `CH4_ALQ_SURF_EQUIL` | Surface equilibration flux; positive to the atmosphere | `gC m-2 s-1` | `time, lndgrid` |
| `CH4_ALQ_SURF_ADV` | Surface advective flux; positive to the atmosphere | `gC m-2 s-1` | `time, lndgrid` |
| `CH4_ALQ_EBUL_ATM` | Direct atmospheric ebullition loss; positive to the atmosphere | `gC m-2 s-1` | `time, lndgrid` |
| `CH4_ALQ_LAT_NET` | Net lateral methane flux; positive out of the soil column | `gC m-2 s-1` | `time, lndgrid` |
| `CH4_ALQ_TRANSPORT_NET_vr` | Net methane transport tendency by soil layer | `gC m-3 s-1` | `time, levdcmp, lndgrid` |

```{warning}
`FCH4` and `CH4FLUX_ALQUIMIA` are not aliases. `FCH4` is the surface flux from
ELM's standard methane formulation and is commonly stored in `kgC m-2 s-1`.
`CH4FLUX_ALQUIMIA` is the total flux from the coupled redox/Alquimia pathway
and is stored in `gC m-2 s-1`. Select the variable associated with the methane
formulation being evaluated, and always verify the units in the file.
```

#### Soil Carbon And Chemistry Profiles

The following variables have dimensions `(time, levdcmp, lndgrid)`:

| Variables | Contents | Typical units |
| --- | --- | --- |
| `DOC_vr`, `DIC_vr`, `CH4_vr` | ELM dissolved organic carbon, inorganic carbon, and methane profiles | `gC m-3` |
| `soil_CO2_aq`, `soil_DOM1`, `soil_acetate`, `soil_MeC`, `soil_H2` | Coupled aqueous carbon substrates, products, and hydrogen | `mol m-3` |
| `soil_O2`, `soil_sulfate`, `soil_sulfide` | Oxygen and sulfur redox species | `mol m-3` |
| `soil_Fe2`, `soil_Fe3` | Dissolved reduced and oxidized iron species | `mol m-3` |
| `soil_FeOxide`, `soil_FeS` | Iron oxide and iron sulfide mineral concentrations | `mol Fe m-3` |
| `soil_Cl`, `soil_Na` | Dissolved chloride and sodium | `mol m-3` |
| `soil_pH` | Soil pH | dimensionless |
| `soil_salinity` | Soil salinity | `ppt` |

The `soil_*` variables are bulk concentrations reported by the coupled model.
They are not automatically converted to porewater concentrations. Check the
variable metadata and model definition before comparing them with porewater
measurements.

#### Alquimia Reaction Rates

Reaction-rate diagnostics begin with `ALQRATE_`. They are vertical profiles
with dimensions `(time, levdcmp, lndgrid)` and units of `mol m-3 s-1`.

| Variable | Reaction represented |
| --- | --- |
| `ALQRATE_ACET_METH` | Acetoclastic methanogenesis |
| `ALQRATE_H2_METH` | Hydrogenotrophic methanogenesis |
| `ALQRATE_MEC_METH` | Methylotrophic methanogenesis |
| `ALQRATE_CH4_O2` | Aerobic methane oxidation |
| `ALQRATE_CH4_SO4` | Sulfate-dependent methane oxidation |
| `ALQRATE_CH4_FE3` | Fe(III)-dependent methane oxidation |
| `ALQRATE_ACET_O2` | Aerobic acetate respiration |
| `ALQRATE_ACET_SO4` | Acetate sulfate reduction |
| `ALQRATE_ACET_FE3` | Acetate Fe(III) reduction |
| `ALQRATE_DOM1_FERM` | DOM1 fermentation |
| `ALQRATE_DOM1_O2` | Aerobic DOM1 respiration |
| `ALQRATE_MEC_FERM` | Methylated-carbon fermentation |
| `ALQRATE_MEC_O2` | Aerobic methylated-carbon respiration |

Rate signs follow the PFLOTRAN kinetic reaction-extent convention. Inspect the
active chemistry deck and reaction stoichiometry before interpreting a sign as
species production or consumption.

## Inspecting And Analyzing Output

### Confirm The Run Finished

The existence of a history file alone does not prove that the run finished.
Check the scheduler status, then search `cpl.log` for successful termination:

```bash
grep "SUCCESSFUL TERMINATION" cpl.log
```

A successful run should contain a line similar to:

```text
SUCCESSFUL TERMINATION OF CPL7-e3sm
```

If that line is absent, inspect `cpl.log`, `lnd.log`, `e3sm.log.<job-id>`, and
the Slurm output before analyzing partial history files.

### Inspect Files From The Command Line

List every file in the first history stream:

```bash
ls -lh *.elm.h0.*.nc
```

Do not inspect only the first matching file. Multiple `h0` files can contain
consecutive portions of the same simulation.

View the authoritative dimensions, variables, and metadata for one file:

```bash
ncdump -h <case-name>.elm.h0.<date>.nc | less
```

Search the header for a particular variable:

```bash
ncdump -h <case-name>.elm.h0.<date>.nc | grep -A6 "CH4FLUX_ALQUIMIA"
```

### Open History Files With Python

#### Open One File With Xarray

```python
import xarray as xr

history_file = "path/to/case.elm.h0.2012-01-01-00000.nc"

with xr.open_dataset(history_file) as dataset:
    print(dataset)
    print(list(dataset.data_vars))
    print(dataset["CH4FLUX_ALQUIMIA"])
    print(dataset["CH4FLUX_ALQUIMIA"].attrs)
```

The printed attributes include the variable's description, units, and time
aggregation method.

#### Open A Complete History Sequence

The workbench output utilities find and combine all matching files, skip empty
history files, sort and deduplicate time, and select the point-site grid cell:

```python
from wetland_redox_workbench.elm_output import (
    normalize_history_time,
    open_case_history,
    scalar_timeseries,
)

run_dir = "path/to/run/directory"

with open_case_history(
    run_dir,
    variables=["GPP", "CH4FLUX_ALQUIMIA", "soil_O2"],
) as history:
    history = normalize_history_time(history, position="start")

    gpp = scalar_timeseries(history, "GPP")
    methane_flux = scalar_timeseries(history, "CH4FLUX_ALQUIMIA")
    oxygen_profile = history["soil_O2"]

    print(gpp)
    print(methane_flux)
    print(oxygen_profile)
```

`scalar_timeseries()` rejects variables with unresolved depth, PFT, or column
dimensions. This is intentional: it prevents a profile from being silently
treated as a site-level time series.

For a profile, select a layer explicitly or retain the complete profile:

```python
surface_oxygen = oxygen_profile.isel(levdcmp=0)
oxygen_near_10cm = oxygen_profile.sel(levdcmp=0.10, method="nearest")
```

Check the selected coordinate value after nearest-neighbor selection:

```python
print(oxygen_near_10cm["levdcmp"].item())
```

### First Analysis Checks

1. Confirm `cpl.log` reports successful termination.
2. List and open all history files belonging to the stream.
3. Check the time range, record count, calendar, and `time_bounds`.
4. Check every analysis variable's units, dimensions, and `cell_methods`.
5. Plot or summarize a few basic fields such as `GPP`,
   `CH4FLUX_ALQUIMIA`, `ZWT`, and `soil_O2` before calculating derived results.
6. Preserve the run namelists, source version, and input paths with the results
   so the run can be reproduced.

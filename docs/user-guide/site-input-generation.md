# Creating Point-Site Inputs

The workbench can create the core static inputs for a one-gridcell
ELM-Wet-Redox site. The tools make mechanically valid files and record where
their values came from. They do not decide whether inherited global values or
user-supplied overrides are scientifically appropriate.

## What The Tools Create

| Product | Tool | Starting information |
| --- | --- | --- |
| Point domain and static wetland surface files | `create_point_site_inputs.py` | Site YAML plus global ELM domain and surface files |
| Wetland water-level forcing | `create_wetland_forcing.py` | Complete regular CSV time series |
| ELM parameter-file copy or one-parameter edit | `create_elm_parameter_file.py` | Tested ELM parameter NetCDF |


## Enter The Environment

With the July 2026 OSC installation:

```bash
source /fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/setup_env.sh
conda activate "$ELM_WET_REDOX_CONDA_ENV"

export SITE_TOOLS="$ELM_WET_REDOX_SITE_TOOLS"
export SITE_WORK="$HOME/elm-site-inputs/NEW-SITE"
mkdir -p "$SITE_WORK"
```

For a source checkout, replace `$SITE_TOOLS` with the workbench repository and
either install the package or place its `src` directory on `PYTHONPATH`.

## Domain And Surface Configuration

Copy the LA2 example as a starting point:

```bash
cp "$SITE_TOOLS/templates/site-inputs/US-LA2.yaml" \
  "$SITE_WORK/site.yaml"
```

The version-1 YAML has four sections:

| Section | Purpose |
| --- | --- |
| `site` | Site name, latitude, longitude, and optional represented area |
| `domain` | Source global ELM domain file |
| `surface` | Source global surface file, PFT choices, and optional overrides |
| `outputs` | Names of the generated domain and surface files |

At minimum, set:

```yaml
version: 1

site:
  name: NEW-SITE
  latitude: 00.0000
  longitude: -00.0000

domain:
  source_file: /path/to/global-domain.nc

surface:
  source_file: /path/to/global-surface.nc
  natural_pft_index: 13
  wetland_pft_count: 5
  wetland_pft_index: 4

outputs:
  domain_file: domain_NEW-SITE.nc
  surface_file: surfdata_NEW-SITE_wetland.nc
```


If `site.area_km2` is omitted, the domain and surface retain the representative
area of the nearest source gridcell. Set it only when the physical area
represented by the point is known.

### Optional Surface Overrides

`surface.variable_overrides` can replace a gridcell scalar or an array whose
final dimension is `gridcell`. The supplied values must match the remaining
NetCDF dimensions exactly. For example:

```yaml
surface:
  variable_overrides:
    PCT_SAND: [40, 40, 40, 40, 40, 40, 40, 40, 40, 40]
    PCT_CLAY: [20, 20, 20, 20, 20, 20, 20, 20, 20, 20]
```

### Generate And Inspect

```bash
python "$SITE_TOOLS/scripts/create_point_site_inputs.py" \
  --config "$SITE_WORK/site.yaml" \
  --output-dir "$SITE_WORK/inputs"
```

The output directory contains the two configured NetCDF files and
`site_input_summary.json`. The summary records requested and selected
coordinates, source files and cell indices, area, and PFT choices.

The generator:

- selects the nearest active global domain cell;
- moves its center and vertices to the requested coordinates;
- sets the one-point domain mask and land fraction to one;
- selects the nearest valid global surface cell;
- sets the output to 100% wetland;
- assigns 100% of the natural and wetland PFT fractions to the configured
  indices; and
- applies only the explicitly requested overrides.

Inspect important values before running:

```bash
ncks -H -C -v xc,yc,xv,yv,mask,frac,area \
  "$SITE_WORK/inputs/domain_NEW-SITE.nc"

ncks -H -C \
  -v LONGXY,LATIXY,AREA,PFTDATA_MASK,PCT_WETLAND,PCT_NATVEG,PCT_NAT_PFT,PCT_WFT \
  "$SITE_WORK/inputs/surfdata_NEW-SITE_wetland.nc"
```

## Wetland Water-Level Forcing

Prepare a CSV with one timestamp and one water-level value per forcing
interval:

```text
time,water_level_m
1850-01-01,0.10
1850-01-02,0.12
```

Create the NetCDF:

```bash
python "$SITE_TOOLS/scripts/create_wetland_forcing.py" \
  --csv "$SITE_WORK/water-level.csv" \
  --time-column time \
  --water-level-column water_level_m \
  --water-level-units m \
  --site-name NEW-SITE \
  --lat 00.0000 \
  --lon -00.0000 \
  --output "$SITE_WORK/inputs/wetland_boundary_forcing_NEW-SITE.nc"
```

The output contains `water_level(time, gridcell)` in meters relative to the
soil surface, positive upward. The converter drops February 29 by default and
requires a complete regular no-leap period with no duplicate timestamps,
gaps, or missing water levels.

Use `--time-resolution-days 1/24` for hourly input or `1/48` for half-hourly
input. Water-level input units may be `m` or `mm`.

Confirm the observed reference datum, sign convention, time zone, timestamp
position, gap-filling method, and treatment timing before converting a
scientific dataset.

## ELM Parameter File

A new coordinate does not automatically need different model parameters.
Make an unchanged, traceable copy of a tested baseline:

```bash
PYTHONPATH="$SITE_TOOLS/src" \
python "$SITE_TOOLS/scripts/create_elm_parameter_file.py" \
  --source /path/to/tested-parameters.nc \
  --output "$SITE_WORK/inputs/clm_params_baseline.nc"
```

To change one value in a named experiment:

```bash
PYTHONPATH="$SITE_TOOLS/src" \
python "$SITE_TOOLS/scripts/create_elm_parameter_file.py" \
  --source /path/to/tested-parameters.nc \
  --output "$SITE_WORK/inputs/clm_params_flnr_test.nc" \
  --variable flnr \
  --index 13 \
  --value 0.15 \
  --expected-source-value 0.1365
```

The output must not already exist. `--expected-source-value` is an optional
guard that prevents silently editing an unexpected baseline.

## Chemistry And Initial Conditions

A site-coordinate change does not itself require a different Alquimia
reaction network. Start from a tested normal and AD-spinup deck. See
{doc}`reaction-network-configuration` before regenerating a network.

Changes to species or reaction topology normally require a compatible new
spinup.

## Validate And Launch

First use the generated inputs in a one-day point-site smoke test. After that
passes, copy the staged-workflow YAML and replace its `inputs` paths with the
generated files. See {doc}`launch-tools` for both launch paths and
{doc}`running-the-model` for the full AD-to-final-to-transient workflow.

The July 2026 LA2 exercise, including known expected values, is available in
{doc}`../workshop/2026-07/day1-create-site-inputs`.

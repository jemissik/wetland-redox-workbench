# Day 1: Create Point-Site Inputs

This exercise creates a new set of point-site inputs from the standard
global ELM files, using LA2 as an example.

For a reusable reference outside the workshop sequence, see
[Creating Point-Site Inputs](../../user-guide/site-input-generation.md).

## Which Files Are Site-Specific?

| File | New for every site? | Day 1 approach |
| --- | --- | --- |
| Domain | Yes | Create from coordinates and the nearest global domain cell |
| Surface | Yes | Extract the nearest valid global surface cell, then apply explicit wetland, soil, PFT, and vegetation choices |
| Wetland boundary forcing | Yes | Convert a complete regular CSV time series to no-leap NetCDF |
| Meteorological forcing | Not necessarily | Use shared global GSWP3 forcing, selected through the point coordinates |
| ELM parameter file | Only when parameters change | Start from the tested shared baseline; make a copied file for an experiment |
| Reaction deck | Only when chemistry changes | Start from the tested shared deck; regenerate only for a documented network choice |

The surface generator uses the global static surface dataset for simulation
year 2000. That matches the current LA2 point-site setup. It does not create a
historical land-use time series or a separate 1850 surface file.

## Enter The Environment

```bash
source /fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/setup_env.sh
conda activate "$ELM_WET_REDOX_CONDA_ENV"
```

Set the shared tool and personal workspace paths:

```bash
export SITE_TOOLS="$ELM_WET_REDOX_SITE_TOOLS"
export SITE_WORK="$HOME/elm-wet-redox-workshop/site-inputs/US-LA2"
mkdir -p "$SITE_WORK"
```

Do not use `/tmp` for model inputs. OSC compute nodes cannot see files in the
login node's local `/tmp`.

## Create The Domain And Surface Files

Copy the LA2 example configuration:

```bash
cp "$SITE_TOOLS/templates/site-inputs/US-LA2.yaml" "$SITE_WORK/site.yaml"
```

Open `site.yaml` and inspect these choices:

- site name, latitude, and longitude;
- optional represented area;
- source global domain and surface files;
- ELM natural-PFT index;
- optional soil overrides.

Generate the two files:

```bash
python "$SITE_TOOLS/scripts/create_point_site_inputs.py" \
  --config "$SITE_WORK/site.yaml" \
  --output-dir "$SITE_WORK/inputs"
```

The output directory contains:

```text
domain_US-LA2.nc
surfdata_US-LA2_wetland.nc
site_input_summary.json
```

The JSON summary records the requested coordinates, source files, nearest
source-cell coordinates and indices, area, and PFT choices.

Inspect the central domain values:

```bash
ncks -H -C -v xc,yc,xv,yv,mask,frac,area \
  "$SITE_WORK/inputs/domain_US-LA2.nc"
```

Inspect the most important surface choices:

```bash
ncks -H -C \
  -v LONGXY,LATIXY,AREA,PFTDATA_MASK,PCT_WETLAND,PCT_NATVEG,PCT_NAT_PFT,PCT_WFT \
  "$SITE_WORK/inputs/surfdata_US-LA2_wetland.nc"
```

For LA2, the generator selects global surface cell `(239, 539)`, centered at
`29.75 N, 269.75 E`, and moves the output coordinates to
`29.8587 N, 269.7131 E`.


### Adapting The YAML To Another Site

At minimum, change:

```yaml
site:
  name: NEW-SITE
  latitude: 00.0000
  longitude: -00.0000
```

Then make decisions about:

- whether the nearest global soil profile is an acceptable first estimate;
- whether measured sand, clay, or organic matter
  should override global values;
- whether patch types should be separate cases or model patches.


## Create Wetland Boundary Forcing From CSV

The example CSV has one row per day:

```text
time,water_level_m
1850-01-01,0.194043300183378
1850-01-02,0.183235600529034
...
```

Copy it and create a forcing file:

```bash
cp "$SITE_TOOLS/templates/site-inputs/US-LA2-water-level-1850.csv" \
  "$SITE_WORK/water-level.csv"

python "$SITE_TOOLS/scripts/create_wetland_forcing.py" \
  --csv "$SITE_WORK/water-level.csv" \
  --time-column time \
  --water-level-column water_level_m \
  --water-level-units m \
  --site-name US-LA2 \
  --lat 29.8587 \
  --lon 269.7131 \
  --output "$SITE_WORK/inputs/wetland_boundary_forcing_US-LA2.nc"
```

The converter:

- accepts meters or millimeters;
- drops February 29 by default;
- requires a complete regular no-leap period;
- rejects duplicate times, gaps, and missing water-level values; and
- records the source CSV, units, site coordinates, and forcing period.

Water level is in meters relative to the soil surface, with positive values
above the surface.

Inspect the result:

```bash
ncdump -h "$SITE_WORK/inputs/wetland_boundary_forcing_US-LA2.nc"
ncks -H -C -v start_year,end_year,time_resolution_days,water_level \
  "$SITE_WORK/inputs/wetland_boundary_forcing_US-LA2.nc" | head -n 35
```

## Choose An ELM Parameter File

A new site does not automatically require new ELM physiology parameters.
Begin with the tested file unless there is a documented reason to change a
model or PFT parameter:

```bash
export LA2_DATA=/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/US-LA2

PYTHONPATH="$SITE_TOOLS/src" \
python "$SITE_TOOLS/scripts/create_elm_parameter_file.py" \
  --source "$LA2_DATA/clm_params_cbgc_c07292018_Add_h2osfc_max_Forc.nc" \
  --output "$SITE_WORK/inputs/clm_params_baseline.nc"
```

For an experiment, create a separate file rather than editing the baseline.
This example changes `flnr` for zero-based PFT index 13:

```bash
PYTHONPATH="$SITE_TOOLS/src" \
python "$SITE_TOOLS/scripts/create_elm_parameter_file.py" \
  --source "$LA2_DATA/clm_params_cbgc_c07292018_Add_h2osfc_max_Forc.nc" \
  --output "$SITE_WORK/inputs/clm_params_flnr_test.nc" \
  --variable flnr \
  --index 13 \
  --value 0.15 \
  --expected-source-value 0.1365
```

Use the unchanged baseline for the first site smoke test.

## Choose Or Generate A Reaction Deck

A site coordinate change does not require a new reaction network. The safest
first test copies the validated LA2 normal and AD-spinup decks:

```bash
cp "$LA2_DATA/CTC_alquimia_forELM_O2consuming.in" \
  "$SITE_WORK/inputs/CTC_alquimia_forELM_O2consuming.in"

cp "$LA2_DATA/CTC_alquimia_forELM_O2consuming_adspinup.in" \
  "$SITE_WORK/inputs/CTC_alquimia_forELM_O2consuming_adspinup.in"
```

To demonstrate generation of the same general MeC-enabled topology:

```bash
export REACTION_TOOLS="$ELM_WET_REDOX_SOFTWARE_ROOT/REDOX-PFLOTRAN"
mkdir -p "$SITE_WORK/generated-reaction-decks"
cd "$REACTION_TOOLS"

python network_for_ELM.py \
  --config configs/elm_reaction_network_parameters.yaml \
  --network-topology mec_minimal \
  --output-dir "$SITE_WORK/generated-reaction-decks"
```

The command creates the collection of standard Alquimia decks. The
`CTC_alquimia_forELM_O2consuming.in` variant is used by the Day 1 chemistry
smoke test.

Note that changing reaction topology normally requires a new compatible spinup.

## Run A One-Day Generated-Input Test

Only do this after the generated files have been inspected. Use the unchanged
baseline parameter file and validated chemistry deck first:

```bash
export CASE_PREFIX="generated_la2_${USER}_20260728"

"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/launch_point_site_smoke.sh" \
  --case-prefix "$CASE_PREFIX" \
  --site-name US-LA2 \
  --domain-file "$SITE_WORK/inputs/domain_US-LA2.nc" \
  --surface-file "$SITE_WORK/inputs/surfdata_US-LA2_wetland.nc" \
  --parameter-file "$SITE_WORK/inputs/clm_params_baseline.nc" \
  --alquimia-file "$SITE_WORK/inputs/CTC_alquimia_forELM_O2consuming.in" \
  --wetland-forcing "$SITE_WORK/inputs/wetland_boundary_forcing_US-LA2.nc"
```

This launcher uses the global GSWP3 meteorological forcing and the generated
domain coordinates. It creates a new build for the participant, stages a
writable chemistry deck, and submits a one-day cold-start case.

Before starting a long spinup, first confirm:

- Slurm reports `COMPLETED` with exit code `0:0`;
- `cpl.log` reports successful termination;
- history and restart files exist;
- the intended generated files appear in `lnd_in`; and
- the assumptions in the surface, parameter, and chemistry files are recorded.

## Use The Generated Files In A Staged Workflow

The one-day launcher checks that the generated files can be used together. A
scientific run uses the separate YAML workflow tool to connect AD spinup, final
spinup, and transient stages.

Copy the tested LA2 workflow template beside the generated inputs:

```bash
cp "$SITE_TOOLS/templates/run-workflows/US-LA2-full.yaml" \
  "$SITE_WORK/run-workflow.yaml"
```

Edit the copy. Choose a unique case prefix, change the site name, and point the
`inputs` entries to the generated files:

```yaml
workflow:
  case_prefix: new_site_full_example
  site_name: NEW-SITE

inputs:
  domain_file: ${CONFIG_DIR}/inputs/domain_NEW-SITE.nc
  surface_file: ${CONFIG_DIR}/inputs/surfdata_NEW-SITE_wetland.nc
  parameter_file: ${CONFIG_DIR}/inputs/clm_params_baseline.nc
  wetland_forcing_file: ${CONFIG_DIR}/inputs/wetland_boundary_forcing_NEW-SITE.nc

  alquimia:
    ad_spinup: ${CONFIG_DIR}/inputs/CTC_alquimia_forELM_O2consuming_adspinup.in
    normal: ${CONFIG_DIR}/inputs/CTC_alquimia_forELM_O2consuming.in
```

`${CONFIG_DIR}` means the directory containing `run-workflow.yaml`. Also
review the run periods, walltimes, restart intervals, history settings, and
model assumptions under `model` and `stages`.

Inspect the resolved workflow without creating cases:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" plan \
  --config "$SITE_WORK/run-workflow.yaml"
```

To create only the AD-spinup case for inspection:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" prepare \
  --config "$SITE_WORK/run-workflow.yaml" \
  --stage ad_spinup
```

After the site inputs and configuration have been reviewed, the same tool can
submit one stage or the complete dependency chain. See the
[Day 1 guide](day1-guide.md) and the
[general run-workflow guide](../../user-guide/running-the-model.md) before
starting a long run.

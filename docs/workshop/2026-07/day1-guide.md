# Day 1: Run ELM-Wet-Redox On OSC

We will be using the LA2 wetland site as a example. The short run is an
infrastructure and workflow test, not a scientifically interpretable
simulation. Longer, previously completed LA2 output will be used for analysis.

Goals:
- Model overview and features;
- Software overview: ELM, Alquimia, PFLOTRAN, CIME, OLMT, and the
  workbench;
- Overview of model inputs;
- Create, submit, monitor, and verify a short ELM-Wet-Redox run;
- Create and inspect point-site input files from the global ELM files; and
- Identify the data and decisions needed to adapt the workflow to a new site.

## Model overview

Begin with {doc}`../../user-guide/model-overview`.

ELM advances the physical land and vegetation state. Alquimia carries
information between ELM and PFLOTRAN. PFLOTRAN solves the configured chemical
reaction network and returns updated chemical state and rates to ELM.

## Software Used In The Workshop

The software stack has two layers:

| Layer | Components | What they do |
| --- | --- | --- |
| Scientific model | ELM-Wet-Redox, Alquimia, PFLOTRAN, and PETSc | Simulate the wetland land surface, soil chemistry, redox reactions, and methane |
| Run and analysis tools | CIME, OLMT, Slurm, the workbench, and later BOA | Configure, build, schedule, analyze, and optimize simulations |

For Day 1, all required software is already installed in shared project
storage. Participants will use that read-only installation to create their own
writable CIME cases, builds, and run directories. Understanding which component
does which job is more important today than learning how to install or compile
each dependency.


## Workshop Paths

The shared workshop installation is readable by project members and should not
be edited. Your cases and model output are written under your home directory.

| Contents | Path | Access |
| --- | --- | --- |
| Shared model, OLMT, libraries, environment, and launcher | `/fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07` | Read and execute |
| Standard E3SM input data | `/fs/ess/PAS0409/e3sm/inputdata` | Read |
| LA2 site inputs | `/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/US-LA2` | Read |
| Preserved LA2 output | `/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/saved-output/US-LA2-baseline-2012-2013` | Read |
| Your CIME case directories | `~/e3sm_cases` | Write |
| Your build and run directories | `~/e3sm_scratch` | Write |
| Your CIME machine configuration | `~/.cime` | Write |

The launcher also stages a private, writable copy of the Alquimia input deck
under `~/e3sm_scratch/workshop-alquimia-inputs`. This is necessary because
Alquimia writes a companion text file beside the deck while the model runs.

### Source, Case, Build, And Run Directories

These directories serve different purposes:

| Directory | What it contains |
| --- | --- |
| Source | Model and case-tool code used to create or build a case |
| Input data | Domain, surface, forcing, parameter, chemistry, and other files read by the model |
| Case | CIME configuration, generated namelists, scripts, job settings, and a record of setup/submission |
| Build | Compiled objects, libraries, and the model executable |
| Run | Runtime namelists, staged inputs, logs, history files, and restart files |


## Enter The Shared Environment

Log in to Cardinal and run:

```bash
source /fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/setup_env.sh
conda activate "$ELM_WET_REDOX_CONDA_ENV"
```

Confirm the environment and create the personal roots if they do not already
exist:

```bash
which python
mkdir -p "$HOME/e3sm_cases" "$HOME/e3sm_scratch"
```

The Python path should begin with:

```text
/fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/conda/envs/elm-pflotran-2026-07
```

The launcher should create these personal directories automatically, but you can also create them directly.

To inspect the pinned source records:

```bash
cat /fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/sources/elm-wet-redox-b3784680/SNAPSHOT_INFO.txt
cat /fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/sources/OLMT-1559d98/SNAPSHOT_INFO.txt
```

## LA2 Inputs

Set a short variable for the shared site directory:

```bash
export LA2_DATA=/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/US-LA2
ls -lh "$LA2_DATA"
```

The example launcher uses these files:

| Input | Purpose |
| --- | --- |
| `domain_sparse_grids_US_LA2_Wetl_C3Gra_c220929.nc` | Grid location, area, land fraction, and mask for the point site |
| `surfdata_sparse_grids_US_LA2_Wetl_C3Gra_c220929_static.nc` | Static landunit, PFT, vegetation, and soil properties |
| `clm_params_cbgc_c07292018_Add_h2osfc_max_Forc.nc` | ELM parameter values, including PFT-level physiology parameters |
| `wetland_boundary_forcing_US_LA2_generic_waterlevel.nc` | Time-varying wetland water level used by the smoke test |
| `CTC_alquimia_forELM_O2consuming.in` | PFLOTRAN/Alquimia species, initial chemistry, reactions, and kinetic parameters |

The launcher also uses standard files under the shared E3SM `inputdata`
directory. For example, the CNP parameter file is standard model input rather
than an LA2-specific file.

NetCDF metadata can be inspected without changing a file:

```bash
ncdump -h "$LA2_DATA/domain_sparse_grids_US_LA2_Wetl_C3Gra_c220929.nc"
ncdump -h "$LA2_DATA/surfdata_sparse_grids_US_LA2_Wetl_C3Gra_c220929_static.nc"
ncdump -h "$LA2_DATA/wetland_boundary_forcing_US_LA2_generic_waterlevel.nc"
```

The [point-site input exercise](day1-create-site-inputs.md) recreates
these LA2 input files from standard global inputs and a water-level CSV.


## Create And Submit A Short LA2 Case

Choose a unique prefix. For example:

```bash
export CASE_PREFIX="la2_day1_${USER}_20260728"
```

The launcher refuses to overwrite an existing case. If you already used this
prefix, choose another one before continuing.

Launch the case:

```bash
/fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/bin/launch_la2_smoke.sh \
  --case-prefix "$CASE_PREFIX"
```

The launcher:

1. loads the tested shared runtime;
2. installs or verifies the workshop CIME machine files in `~/.cime`;
3. validates all required shared inputs;
4. creates personal case, build, run, and chemistry-staging directories;
5. configures and builds a one-day cold-start LA2 case; and
6. submits the model through Slurm using project `PAS0409`.

Save the case name, paths, and Slurm job ID printed at the end. Setup and build
can take several minutes. Queue waiting time is separate; the one-day model
step itself normally takes only seconds.

Set the paths used by the remaining commands:

```bash
export CASE_NAME="${CASE_PREFIX}_US-LA2_ICB1850CNRDCTCBC"
export CASE_DIR="$HOME/e3sm_cases/$CASE_NAME"
export RUN_DIR="$HOME/e3sm_scratch/$CASE_NAME/run"
export SUMMARY="$CASE_DIR/workshop_launch_summary.txt"
cat "$SUMMARY"
```

The summary should contain the case, build, run, and staged Alquimia paths,
the source revisions, and the Slurm job ID.

### Monitor The Job

Read the submitted job ID from the summary:

```bash
export JOB_ID="$(awk -F= '$1 == "slurm_job_id" {print $2}' "$SUMMARY")"
echo "$JOB_ID"
```

Check whether it is queued or running:

```bash
squeue -j "$JOB_ID"
```

The short job may finish before `squeue` is run. Check its final accounting
record with:

```bash
sacct -j "$JOB_ID" --format=JobID,JobName,State,ExitCode,Elapsed
```

Common states include:

| State | Meaning |
| --- | --- |
| `PENDING` | Waiting for resources or another scheduler condition |
| `RUNNING` | Running on a compute node |
| `COMPLETED` | Finished; also confirm exit code `0:0` |
| `FAILED`, `TIMEOUT`, or `CANCELLED` | Did not complete as requested; inspect logs before rerunning |

### Verify The Run

After the job completes, confirm successful model termination:

```bash
grep "SUCCESSFUL TERMINATION" "$RUN_DIR/cpl.log"
```

List the ELM history and restart files:

```bash
ls -lh "$RUN_DIR"/*.elm.h0.*.nc
ls -lh "$RUN_DIR"/*.elm.r.*.nc "$RUN_DIR"/*.elm.rh0.*.nc
```

The run is successful when:

- Slurm reports `COMPLETED` with exit code `0:0`;
- `cpl.log` contains `SUCCESSFUL TERMINATION`;
- the recorded paths point to your own home directory;
- at least one nonempty `.elm.h0.*.nc` history file exists

If setup fails, inspect the case-specific launcher log:

```bash
tail -n 80 "$HOME/e3sm_cases/workshop-launch-logs/$CASE_NAME.log"
```

Do not delete a failed case immediately. Its configuration and logs are useful
for diagnosis. Use a new prefix for another attempt.

## Archived Output

A completed 2012–2013 LA2 trial is available at:

```bash
export SAVED_TRIAL=/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/saved-output/US-LA2-baseline-2012-2013
export SAVED_RUN="$SAVED_TRIAL/run"
cat "$SAVED_TRIAL/README.md"
ls -lh "$SAVED_RUN"/*.elm.h0.*.nc
grep "SUCCESSFUL TERMINATION" "$SAVED_RUN/cpl.log"
```

This bundle contains two full years of history output, restart state,
configuration, logs, trial parameters, provenance manifests, and aligned GPP
and methane metric tables.

See the [model-output guide](../../user-guide/model-outputs.md) for details
about the run directory, history variables, restart files, dimensions, units,
and time coordinates.

## Spinup, Restart, And Transient Runs

The short smoke test we ran was just to check that the model infrastructure is working properly.
A scientific simulation normally uses a staged sequence:

| Stage | Purpose | Scientific use |
| --- | --- | --- |
| Accelerated-decomposition spinup | Move slow carbon pools toward a repeating state more quickly | Intermediate state; do not analyze as a normal simulation |
| Final spinup | Continue with normal process rates and the intended reaction network | Produces the restart used by the transient run |
| Transient or experiment | Apply historical forcing, observed water levels, or a treatment scenario | Main analysis period |

The handoff between stages uses restart files:

```text
<case>.elm.r.<date>.nc
<case>.elm.rh0.<date>.nc
<case>.cpl.r.<date>.nc
rpointer.lnd
rpointer.drv
```

History files (`.elm.h0.*.nc`) are for analysis. They do not contain the full
state required to restart the model.

A restart is tied to the model structure, parameterization, chemistry network,
and date that produced it. Structural changes can require a new spinup.


### Prepare Or Start A Spinup Workflow

The reusable workflow is defined in YAML. Copy the LA2 example to a writable
directory:

```bash
mkdir -p "$HOME/elm-workshop/workflows"
cp "$ELM_WET_REDOX_SITE_TOOLS/templates/run-workflows/US-LA2-full.yaml" \
  "$HOME/elm-workshop/workflows/la2-full.yaml"
```

Open the copy and choose a unique `workflow.case_prefix`. Before submitting
anything, inspect the resolved cases, inputs, and restart handoffs:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" plan \
  --config "$HOME/elm-workshop/workflows/la2-full.yaml"
```

The workshop template intentionally leaves `paths.executable_root` unset.
During AD preparation, the workflow builds `e3sm.exe` once beneath the
participant's writable `run_root`. Final spinup and transient preparation then
reuse that personal build.

To create only the AD-spinup case for inspection:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" prepare \
  --config "$HOME/elm-workshop/workflows/la2-full.yaml" \
  --stage ad_spinup
```

After reviewing the case, submit that stage with:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" submit \
  --config "$HOME/elm-workshop/workflows/la2-full.yaml" \
  --stage ad_spinup
```

The complete AD-to-final-to-transient chain can instead be prepared and
submitted with one `run` command. Do this only after the input files, stage
durations, walltimes, and scientific configuration have been reviewed:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" run \
  --config "$HOME/elm-workshop/workflows/la2-full.yaml"
```

For a new site, start from the same YAML and replace the site name and
site-specific input paths with the files created in the
[point-site input exercise](day1-create-site-inputs.md). AD preparation
compiles the selected `model_root` once, and the later stages reuse that
workflow's build. Creating the case is a useful Day 1 checkpoint even when the
long spinup will continue after the workshop.

See the general [run-workflow guide](../../user-guide/running-the-model.md) for
all commands, stage settings, monitoring, and failure behavior.

## Map The Workflow To A New Site

See the [Site Data Checklist](site-data-checklist.md)


### Model Setup And Forcing

High-priority categories include:

- site coordinates, area, and spatial organization;
- soil texture, carbon, bulk density, and depth information;
- vegetation type, patch fraction;
- water table, surface-water depth;
- salinity and available boundary-water chemistry;

### Evaluation And Parameterization

Potential targets include:

- GPP, CO2 flux, and methane flux;
- porewater CH4, CO2/DIC, salinity, pH, EC, sulfate, and oxygen by depth;
- before/after anomalies and treatment-versus-control contrasts.


## Day 1 Record

Before finishing, save these values:

| Item | Value |
| --- | --- |
| Case name | |
| Case directory | |
| Build directory | |
| Run directory | |
| Slurm job ID and final state | |
| Model and OLMT snapshot | |
| History file inspected | |
| Preserved output path for Day 2 | |
| First participant-site scenario to test | |
| Most important missing input or metadata | |

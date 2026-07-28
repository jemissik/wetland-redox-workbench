# Launch Tools

ELM-Wet-Redox has separate tools for infrastructure checks and scientific
multi-stage simulations. Choose the tool based on what you need to establish.

| Tool | Use it for |
| --- | --- |
| `launch_la2_smoke.sh` | Confirming the shared OSC installation with the prepared LA2 inputs
| `launch_point_site_smoke.sh` | Checking that one site's domain, surface, parameter, chemistry, and wetland-forcing files run together
| `run_elm_workflow.py` | Preparing and submitting AD spinup, final spinup, and transient stages separately or as one dependency chain

The two smoke launchers run one cold-start day. Their output only establishes
that setup, compilation, input staging, Slurm submission, and model execution
work. A scientifically interpretable transient should start from a
compatible spinup.

## Enter The OSC Environment

For the July 2026 shared installation:

```bash
source /fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/setup_env.sh
conda activate "$ELM_WET_REDOX_CONDA_ENV"
```

The shared commands are under:

```text
/fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/bin
```

By default, personal CIME cases are written below `~/e3sm_cases`, while builds
and run directories are written below `~/e3sm_scratch`. The launchers create
these roots when needed and refuse to replace an existing case.

## Prepared LA2 Smoke Test

Use the fixed LA2 launcher when checking a new participant account or the
shared installation:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/launch_la2_smoke.sh" \
  --case-prefix "la2_check_${USER}_20260728"
```

The launcher selects the prepared LA2 inputs, installs or verifies the
workshop CIME machine files in `~/.cime`, creates a private case and run
directory, builds the model, and submits a one-day Slurm job.

Use `--model-root` to compile the smoke test from another ELM-Wet-Redox source
tree:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/launch_la2_smoke.sh" \
  --case-prefix "personal_source_check_${USER}_20260730" \
  --model-root "$HOME/elm-wet-redox"
```

Run `launch_la2_smoke.sh --help` to see the source, OLMT, case-root, and
output-root overrides.

## General Point-Site Smoke Test

Use the point-site launcher after creating or changing site inputs:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/launch_point_site_smoke.sh" \
  --case-prefix "new_site_check_${USER}_20260728" \
  --site-name NEW-SITE \
  --domain-file /path/to/domain_NEW-SITE.nc \
  --surface-file /path/to/surfdata_NEW-SITE_wetland.nc \
  --parameter-file /path/to/clm_params_baseline.nc \
  --alquimia-file /path/to/CTC_alquimia_forELM_O2consuming.in \
  --wetland-forcing /path/to/wetland_boundary_forcing_NEW-SITE.nc
```

This launcher currently targets one-gridcell OSC/Cardinal cases using shared
GSWP3 meteorological forcing. It stages a writable case-specific copy of the
Alquimia deck because Alquimia writes an output file beside that deck.

The optional `--exeroot` argument reuses a compatible existing build. This is
an advanced option. The executable must have been built from the intended
`--model-root` revision with the compiler, MPI library, and compile-time
settings required by the case. Omit `--exeroot` after editing model source,
changing branches or commits, changing compile-time options, or whenever the
build provenance is uncertain.

## Staged Scientific Workflow

The YAML workflow tool supports this sequence:

```text
AD spinup -> final spinup -> transient or experiment
```

Start from the shared example:

```bash
mkdir -p "$HOME/elm-workflows"
cp "$ELM_WET_REDOX_SITE_TOOLS/templates/run-workflows/US-LA2-full.yaml" \
  "$HOME/elm-workflows/my-site.yaml"
```

Choose a unique `workflow.case_prefix`, replace the site-specific input paths,
and review the stage durations and walltimes. Inspect the resolved plan before
creating cases:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" plan \
  --config "$HOME/elm-workflows/my-site.yaml"
```

Prepare or submit one stage:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" prepare \
  --config "$HOME/elm-workflows/my-site.yaml" \
  --stage ad_spinup

"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" submit \
  --config "$HOME/elm-workflows/my-site.yaml" \
  --stage ad_spinup
```

Prepare and submit the complete configured dependency chain:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" run \
  --config "$HOME/elm-workflows/my-site.yaml"
```

Inspect Slurm state and expected restart files:

```bash
"$ELM_WET_REDOX_SOFTWARE_ROOT/bin/run_elm_workflow.py" status \
  --config "$HOME/elm-workflows/my-site.yaml"
```

See {doc}`running-the-model` for the YAML fields, restart handoffs, workflow
manifest, provenance checks, failure behavior, and the rules for choosing
`model_root` and `executable_root`.

## Check A Submitted Run

After Slurm finishes, confirm all of the following:

1. `sacct` reports `COMPLETED` and exit code `0:0`.
2. `cpl.log` contains `SUCCESSFUL TERMINATION`.
3. Nonempty ELM history and restart files exist in the run directory.
4. `lnd_in` points to the intended domain, surface, parameter, chemistry,
   forcing, and initial-condition files.
5. Case and run paths are writable personal paths, while shared source and
   baseline inputs remain unchanged.

History files are for analysis; restart files carry model state into the next
stage. See {doc}`model-outputs` for the run-directory layout.

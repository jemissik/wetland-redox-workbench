# Running The Model

ELM-Wet-Redox simulations normally use more than one model stage. The
workbench run-workflow tool creates the CIME cases, connects their restart
files, and can submit the complete sequence through Slurm dependencies.

Use the workflow tool for:

- accelerated-decomposition (AD) spinup;
- final spinup;
- transient or experiment runs; and
- preparing or submitting any of those stages separately.

A one-day smoke-test launcher may still be useful for checking a new
installation. It is not a substitute for scientific spinup.

See {doc}`launch-tools` to choose between the prepared LA2 smoke test, the
general point-site smoke test, and this staged workflow.

## The Stage Sequence

A complete workflow has this dependency order:

```text
AD spinup -> final spinup -> transient or experiment
```

Each arrow represents a restart handoff. The final state written by one stage
becomes the initial state for the next. The cases share one compatible model
executable, but each stage has its own case directory, run directory, logs,
history output, and writable Alquimia deck.

| Stage | Main purpose | Initial state |
| --- | --- | --- |
| `ad_spinup` | Accelerate adjustment of slow carbon pools | Generic model initialization |
| `final_spinup` | Continue spinup with normal decomposition rates | Final AD-spinup restart |
| `transient` | Run the historical or experimental period | Final-spinup restart |

AD-spinup output is an intermediate state and should not be interpreted as a
normal simulation. See the [model-output guide](model-outputs.md) for the
difference between history and restart files.

## Create A Workflow Configuration

Start from the example:

```bash
cp templates/run-workflows/US-LA2-full.yaml my-site-run.yaml
```

Edit the copy. At minimum, choose a unique `workflow.case_prefix` and review
every input path and stage duration. The important top-level sections are:

| Section | Contents |
| --- | --- |
| `workflow` | Unique case prefix and site name |
| `paths` | Model, OLMT, standard input data, CIME template, and writable roots |
| `inputs` | Domain, surface, parameter, forcing, land-use, namelist, and Alquimia files |
| `model` | Machine, compsets, tasks, timestep, nutrient mode, and common history fields |
| `stages` | Stages to run and their duration, walltime, restart interval, and history settings |

A stage is enabled by including its name:

```yaml
stages:
  ad_spinup:
    years: 60
    walltime: "06:00:00"
    restart_every_years: 5

  final_spinup:
    years: 100
    walltime: "16:00:00"
    restart_every_years: 10

  transient:
    start_year: 1850
    end_year: 2013
    walltime: "24:00:00"
    restart_every_years: 5
```

Omit `transient` for a spinup-only workflow. A configured `final_spinup`
requires `ad_spinup`, and a configured `transient` requires both spinup
stages. Empty stage mappings use project defaults, but production durations,
walltimes, and restart intervals should be chosen explicitly.

Paths may contain `${HOME}`, other environment variables, `~`, or
`${CONFIG_DIR}`. Relative paths are resolved from the directory containing
the YAML file.

### Choose The Model Source And Executable

`paths.model_root` selects the ELM-Wet-Redox source tree used to configure and
build the cases. It can point to the pinned read-only shared source or to a
personal writable Git checkout:

```yaml
paths:
  model_root: ${HOME}/elm-wet-redox
```

The optional `paths.executable_root` selects an existing build directory
containing `e3sm.exe`. Supplying it skips the new build and reuses that
executable:

```yaml
paths:
  model_root: /path/to/the/model/source
  executable_root: /path/to/a/compatible/bld
```

These two paths are related but are not interchangeable. `model_root`
identifies the source and case tools; `executable_root` identifies already
compiled code. Changing `model_root` does not rebuild or replace a configured
`executable_root`.

Use `executable_root` when:

- the executable was built from the intended source revision;
- the source has not changed since it was built;
- the machine, compiler, MPI library, and compile-time model options match the
  new case; and
- its provenance is known well enough to record with the run.

Omit `executable_root` when:

- testing source edits or a different branch or commit;
- changing compile-time model options;
- the existing build's source or configuration is uncertain; or
- deliberately creating an independent build for reproducibility.

When it is omitted, AD-spinup preparation builds the executable from
`model_root`, and the downstream stages reuse that new build. Always use a new
`workflow.case_prefix` for a new source version or build. A model change may
also require a new spinup or make an older restart incompatible even when the
code compiles successfully.

## Inspect The Plan

Activate the required Python and model environment, then inspect the resolved
workflow before creating anything:

```bash
python scripts/run_elm_workflow.py plan --config my-site-run.yaml
```

`plan` does not create cases or submit jobs. Review:

- case, build, and run directories;
- source and input paths;
- OLMT commands;
- restart dates between stages; and
- the expected terminal restart for each stage.

Preflight validation also checks explicit PFLOTRAN database paths and compares
the ordered primary, secondary, mineral, immobile, and passive-gas species
blocks in distinct AD and normal decks. These checks catch common stale-path
and restart-topology errors before a job is submitted. They do not establish
that a new reaction network is scientifically or numerically valid.

The workflow refuses to overwrite an existing case. Use a new `case_prefix`
for a scientifically different run or another setup attempt.

## Run The Complete Sequence

To create all configured cases and submit the dependency chain:

```bash
python scripts/run_elm_workflow.py run --config my-site-run.yaml
```

Preparation happens in dependency order. AD spinup builds the executable from
`model_root` unless `executable_root` was supplied. Downstream cases reuse that
build.
Submission then creates Slurm dependencies so final spinup starts only after
AD spinup succeeds, and the transient stage starts only after final spinup
succeeds.

The command creates a workflow record at:

```text
<run_root>/workflows/<case_prefix>_<site_name>/workflow.json
```

It also keeps preparation and submission logs under the workflow's `logs`
directory and writable stage-specific chemistry inputs under `inputs`.

## Work With Stages Separately

Use `prepare` to create cases without submitting:

```bash
python scripts/run_elm_workflow.py prepare \
  --config my-site-run.yaml \
  --stage ad_spinup
```

Use `submit` after reviewing the prepared case:

```bash
python scripts/run_elm_workflow.py submit \
  --config my-site-run.yaml \
  --stage ad_spinup
```

Repeat the commands for `final_spinup` and `transient`. A downstream stage can
be prepared after its predecessor case and shared executable have been
prepared. It can be submitted while the predecessor is still queued or
running; the tool adds the required Slurm dependency.

Omitting `--stage` operates on all configured stages. Repeat `--stage` to
select more than one:

```bash
python scripts/run_elm_workflow.py prepare \
  --config my-site-run.yaml \
  --stage ad_spinup \
  --stage final_spinup
```

## Monitor The Workflow

Check every configured stage with:

```bash
python scripts/run_elm_workflow.py status --config my-site-run.yaml
```

The report includes:

- the Slurm job ID and scheduler state;
- the case and run directories;
- the expected terminal restart path; and
- whether that restart exists.

You can also use normal Slurm commands:

```bash
squeue -u "$USER"
sacct -j JOB_ID --format=JobID,JobName,State,ExitCode,Elapsed,Reason
```

A stage is complete only when Slurm reports `COMPLETED` with exit code `0:0`
and its expected restart exists. The status command records the latest result
in `workflow.json`.

## Failures And Continuation

Slurm dependencies use successful completion. If AD or final spinup fails,
times out, or is cancelled, downstream stages do not start.

Periodic restart checkpoints reduce how much work is lost, but the workflow
tool does not yet create a continuation case automatically. Inspect the failed
stage's CIME and model logs before resubmitting or continuing it. Do not submit
a downstream stage from a missing or incompatible restart.

The YAML file and resolved input-file checksums are part of the run
provenance. Once preparation creates the manifest, changing that YAML causes
later commands to stop. Changing a configured input file or a stage's writable
chemistry copy also causes later workflow operations to stop. Use a new
`case_prefix` for changed configurations rather than making an existing
workflow ambiguous.

## Relation To BOA

This workflow prepares scientifically initialized, traceable model cases.
BOA optimization trials use a different lifecycle: they copy a completed run
template, apply trial parameters, and submit many short independent model
runs using a compatible prebuilt executable.

Do not run the full spinup workflow inside each BOA trial. Instead, finish and
validate the baseline workflow first, then create the BOA run template and
executable references from that baseline.

# Day 2: Analyze Output And Start BOA

Day 2 goals:

1. read and interpret ELM-Wet-Redox history output;
2. compare model results with observations; and
3. start a BOA run.

The main examples use a completed LA2 simulation and saved BOA experiments.

## Model outputs
The general output-file guide is {doc}`../../user-guide/model-outputs`.

## Prepare The Notebook Environment

Day 2 uses a conda environment containing the output-analysis tools, the
workbench modules, and BOA. In a Cardinal terminal, load the shared software
environment and activate its conda environment:

```bash
source /fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/setup_env.sh
conda activate "$ELM_WET_REDOX_CONDA_ENV"
```

Run these commands once in each new terminal session used for model or BOA
work.


Register the combined environment as a Jupyter kernel by running this command
once:

```bash
/fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/conda/envs/elm-wet-redox-boa-2026-07/bin/python \
  -m ipykernel install --user \
  --name elm-boa \
  --display-name "ELM-BOA"
```

This creates a small kernel entry in your account; it does not copy or install
the shared environment. If you registered **ELM-Wet-Redox workshop** during
the earlier setup homework, you still need to run the command above.

In VS Code or JupyterLab, open the kernel selector and choose
**ELM-BOA**. If VS Code does not show it immediately, reload the
remote window and open the kernel selector again.

Run this cell before beginning the analysis:

```python
import sys
from pathlib import Path

import boa
import wetland_redox_workbench

print(f"Python: {Path(sys.executable).resolve()}")
print(f"BOA: {boa.__version__}")
print(f"Workbench: {wetland_redox_workbench.__file__}")
```

The Python path should begin with:

```text
/fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/conda/envs/elm-wet-redox-boa-2026-07
```

The workbench path should begin with:

```text
/fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/site-tools-2026-07/src
```

### Copy The Analysis Notebook

Copy the executed reference notebook into your own writable directory:

```bash
export DAY2_DIR="$HOME/e3sm_scratch/workshop-2026-07/day2"
mkdir -p "$DAY2_DIR"
cp \
  /fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/teaching-materials/day2/day2-la2-output-analysis.ipynb \
  "$DAY2_DIR/"
```

Open the copy at:

```text
~/e3sm_scratch/workshop-2026-07/day2/day2-la2-output-analysis.ipynb
```

The shared notebook already contains reference output, but its code is intended
to be run again. It writes new figures, tables, and provenance to:

```text
~/e3sm_scratch/workshop-2026-07/day2-analysis
```

## Part 1: Analyze LA2 Output

The notebook uses saved output from an LA2 simulation covering 2012 and 2013.
The shared bundle contains the hourly history files, run configuration,
reaction network, and provenance.

This is example output for learning the analysis workflow, not a calibrated
or preferred scientific result.

The exercise:

1. opens one NetCDF file directly with `xarray`;
2. searches variables and inspects dimensions, units, and time metadata;
3. switches to the workbench tools to combine the two annual files;
4. normalizes ELM's no-leap history timestamps;
5. selects the gridcell and soil layers deliberately;
6. checks time coverage, finite values, and output ranges;
7. plots hydrology, ecosystem fluxes, a methane reaction budget, and
   soil chemistry/reaction profiles; and
8. saves figures, aligned tables, summary metrics, and provenance.

The executed reference products are also available without running Jupyter:

```text
/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/teaching-materials/day2/reference-analysis
```

## Part 2: Compare Model Results With Observations

The LA2 example compares:

| Quantity | Model variable | Observation column |
| --- | --- | --- |
| Gross primary production | `GPP` | `GPP_PI_F` |
| Methane flux | `CH4FLUX_ALQUIMIA` | `FCH4_F` |

The comparison makes the following choices explicit:

- observation missing-value handling;
- timestamp interpretation and no-leap calendar treatment;
- unit and sign conversion;
- hourly and daily aggregation;
- minimum data coverage;
- model-observation overlap; and
- the limits of interpreting RMSE by itself.


## Part 3: Understand And Launch BOA

### How A BOA Trial Works

```text
BOA configuration
    -> BOA proposes parameter values
    -> ELMWetRedoxWrapper creates trial inputs
         -> edit an ELM NetCDF parameter file
         -> edit or generate an Alquimia/PFLOTRAN reaction deck
    -> submit the ELM trial through Slurm
    -> read ELM history output
    -> align model output with observations
    -> return metric data to BOA
    -> BOA records the result and proposes another trial
```

BOA does not run the complete spinup chain for every parameter proposal.
`ELMWetRedoxWrapper` starts each short trial from a reviewed run template,
executable, and restart state. Every trial receives private copies of the
files that BOA changes.


### Inspect The Saved LA2 Optimizations

Begin with two completed 30-trial single-objective LA2 experiments:

1. a photosynthesis experiment that varied `flnr` and minimized GPP RMSE; and
2. an Alquimia experiment that varied two methanogenesis rates and minimized
   methane-flux RMSE.

These are independent example experiments.

The group-readable bundle is:

```text
/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/teaching-materials/day2/boa-noh2-2012-2013
```

Read its overview:

```bash
export SAVED_BOA=/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/teaching-materials/day2/boa-noh2-2012-2013
less "$SAVED_BOA/README.md"
column -s, -t "$SAVED_BOA/experiment-summary.csv"
```

Copy the executed single-objective notebook into your writable Day 2
directory:

```bash
export DAY2_DIR="$HOME/e3sm_scratch/workshop-2026-07/day2"
mkdir -p "$DAY2_DIR"
cp \
  "$SAVED_BOA/analysis/day2-boa-single-objective-results.ipynb" \
  "$DAY2_DIR/"
```

Open `day2-boa-single-objective-results.ipynb` with the
**ELM-BOA** kernel. The notebook:

1. loads each archived single-objective client with BOA;
2. confirms the completed trials and actual generation methods;
3. uses BOA's native metric-trace plot;
4. relates the ELM `flnr` parameter to GPP RMSE;
5. relates the two reaction-rate parameters to methane RMSE;
6. compares the center and best observed trials with observations; and
7. traces a BOA reaction-rate proposal into the private trial inputs.

The best photosynthesis trial reduces GPP RMSE by approximately 56% relative
to the center. The best Alquimia trial reduces methane RMSE by approximately
50%, but its acetoclastic rate reaches the configured lower bound. Treat both
as successful workflow and response examples rather than final calibrations.

For one saved trial, identify:

| Question | Artifact |
| --- | --- |
| What values did BOA propose? | Trial metadata and the experiment optimization table |
| What files were changed? | `trial_manifest.json` and the trial's private inputs |
| What model run was submitted? | `run_manifest.json`, Slurm job information, and run directory |
| Did ELM complete successfully? | Poll state, exit state, and ELM/coupler logs |
| Which model and observation values were paired? | Aligned metric tables and metric summary |
| What did BOA retain? | `optimization.csv`, `client.json`, and the experiment log |

#### Optional Multiobjective Extension

The bundle also contains a combined experiment that varies `flnr` and both
reaction rates together while retaining GPP and methane RMSE as separate
objectives. It is a true multiobjective experiment, not a weighted sum.

To inspect objective space and the observed Pareto frontier, copy and open:

```bash
cp \
  "$SAVED_BOA/analysis/day2-boa-combined-noh2-results.ipynb" \
  "$DAY2_DIR/"
```

The combined experiment is an alternative optimization design. It is not the
next stage of the two independent single-objective experiments.

The archived JSON and configuration files preserve their original run paths as
provenance. The results notebook does not depend on those paths. Do not submit
an archived configuration; use the tested launch configuration in the next
section.

### Launch A BOA Optimization

Submit a BOA controller to Slurm. The controller runs 15 one-year ELM trials
covering 2012, with five initialization trials and no more than three trials
pending at once. The objective and tracking metric use the 2012
model-observation overlap.

The tested one-year model trial completed in about six minutes. The 15-trial
optimization will take longer, and Slurm queue time can vary, so continue with
the saved examples while the live optimization runs.

The launch example uses:

- `flnr`, an ordinary ELM PFT parameter;
- an Alquimia methanogenesis rate;
- daily GPP RMSE as the objective; and
- daily methane-flux RMSE as a tracking metric.

Confirm that the shell is using the shared BOA and workbench installation:

```bash
python -c "import boa; print('BOA', boa.__version__)"
python -c "import wetland_redox_workbench as w; print(w.__file__)"
```

Submit the BOA controller:

```bash
export WORKSHOP_ROOT=/fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07
export BOA_LOG_DIR="$HOME/e3sm_scratch/boa-orchestrator-logs"
mkdir -p "$BOA_LOG_DIR"

export BOA_JOB_ID=$(
  sbatch --parsable \
    --job-name="boa_workshop_${USER}" \
    --output="$BOA_LOG_DIR/boa-workshop-%j.out" \
    "$WORKSHOP_ROOT/site-tools-2026-07/scripts/run_boa_optimization.sbatch" \
    "$WORKSHOP_ROOT/site-tools-2026-07/templates/boa/la2-minimal/workshop-lifecycle-config.yaml"
)
echo "BOA controller job: $BOA_JOB_ID"
```

The controller runs BOA and submits separate child Slurm jobs for ELM. Check
the controller with:

```bash
squeue -j "$BOA_JOB_ID"
sacct -j "$BOA_JOB_ID" --format=JobID,JobName,State,ExitCode,Elapsed
```

The controller log records the experiment directory and progress:

```bash
export BOA_LOG="$BOA_LOG_DIR/boa-workshop-${BOA_JOB_ID}.out"
tail -n 50 "$BOA_LOG"
```

Once BOA has started, obtain the experiment directory from the log:

```bash
export BOA_EXPERIMENT=$(
  sed -n 's/^Output Experiment Dir: //p' "$BOA_LOG" | tail -n 1
)
echo "$BOA_EXPERIMENT"
```

After the controller completes, inspect the result:

```bash
cat "$BOA_EXPERIMENT/optimization.csv"
python -m json.tool "$BOA_EXPERIMENT/000000/trial_manifest.json" | less
python -m json.tool "$BOA_EXPERIMENT/000000/poll_state.json" | less
```

To check the child ELM job directly:

```bash
export ELM_JOB_ID=$(
  python -c \
    'import json, sys; print(json.load(open(sys.argv[1]))["slurm_job_id"])' \
    "$BOA_EXPERIMENT/000000/launch_state.json"
)
sacct -j "$ELM_JOB_ID" --format=JobID,JobName,State,ExitCode,Elapsed
```

The launch is successful when:

1. the controller receives a Slurm job ID;
2. private trial directories and manifests appear;
3. the controller submits child ELM jobs;
4. trials begin reaching terminal states;
5. aligned metric data are written; and
6. the experiment contains `optimization.csv` and `client.json`.

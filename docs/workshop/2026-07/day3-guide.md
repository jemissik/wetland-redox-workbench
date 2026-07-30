# Day 3: Parameter Optimization And Next Steps

Day 3 goals:

1. Parameter optimization using BOA
2. Software development practices / working with the code
3. Work on setting up new model experiments
4. Discussion of next steps


## Prepare The Environment

In a new Cardinal terminal, load the shared software and activate the combined
ELM-Wet-Redox/BOA environment:

```bash
source /fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07/setup_env.sh
conda activate "$ELM_WET_REDOX_CONDA_ENV"
```

Use the **ELM-BOA** Jupyter kernel registered during Day 2.

## Objective functions

Return to {ref}`the Day 2 model-observation comparison
<day2-model-observation-comparison>`. The LA2 example compares:

| Quantity | Model variable | Observation column |
| --- | --- | --- |
| Gross primary production | `GPP` | `GPP_PI_F` |
| Methane flux | `CH4FLUX_ALQUIMIA` | `FCH4_F` |

The comparison workflow:

1. loads observations and handles missing values;
2. interprets timestamps and the no-leap calendar;
3. converts units and signs;
4. aggregates model and observation data consistently;
5. checks coverage and overlap; and
6. calculates a metric such as RMSE.

BOA receives the aligned model and observation values and evaluates the metric
defined in its configuration. The metric becomes an **objective** when BOA is
asked to minimize or maximize it (for example, minimize RMSE of model vs observations).

BOA also supports information-only metrics (metrics can be recorded for
interpretation without being optimized).



## Part 2: How A BOA Trial Works

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

The main software pieces are:

| Component | Role |
| --- | --- |
| BOA | Bayesian optimization machinery. Proposes parameter values and records trial results |
| `ELMWetRedoxWrapper` | Implements the BOA wrapper interface for this model |
| Workbench parameter tools | Create ELM and reaction-network inputs |
| Trial launcher | Submits ELM run |
| Workbench analysis tools | Read output, align observations, and return metric data |

BOA does not run the complete spinup chain for every parameter proposal.
`ELMWetRedoxWrapper` starts each short trial from a reviewed run template,
executable, and restart state. Every trial receives copies of the
files BOA changes.


## Part 3: Example Optimizations

Begin with two completed 30-trial single-objective LA2 experiments:

1. a photosynthesis experiment that varied `flnr` and minimized GPP RMSE; and
2. an Alquimia experiment that varied two methanogenesis rates and minimized
   methane-flux RMSE.

These are independent example experiments. The group-readable bundle is:

```text
/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/teaching-materials/day3/boa-noh2-2012-2013
```

Read its overview:

```bash
export SAVED_BOA=/fs/ess/PAS0409/e3sm/project-data/workshop-2026-07/teaching-materials/day3/boa-noh2-2012-2013
less "$SAVED_BOA/README.md"
column -s, -t "$SAVED_BOA/experiment-summary.csv"
```

Copy the executed single-objective notebook into a writable Day 3 directory:

```bash
export DAY3_DIR="$HOME/e3sm_scratch/workshop-2026-07/day3"
mkdir -p "$DAY3_DIR"
cp \
  "$SAVED_BOA/analysis/day3-boa-single-objective-results.ipynb" \
  "$DAY3_DIR/"
```

Open `day3-boa-single-objective-results.ipynb` with the **ELM-BOA** kernel. The
notebook:

1. loads each archived single-objective client with BOA;
2. confirms completed trials and the actual generation methods;
3. uses BOA's native metric-trace plot;
4. relates the ELM `flnr` parameter to GPP RMSE;
5. relates two reaction-rate parameters to methane RMSE;
6. compares center and best observed trials with observations; and
7. traces a BOA reaction-rate proposal into private trial inputs.

The best photosynthesis trial reduces GPP RMSE by approximately 56% relative
to the center. The best Alquimia trial reduces methane RMSE by approximately
50%, but its acetoclastic rate reaches the configured lower bound.

### Example Multiobjective optimization

The bundle also contains a combined experiment that varies `flnr` and both
reaction rates together while retaining GPP and methane RMSE as separate
objectives. It is a true multiobjective experiment, not a weighted sum.

Copy and open:

```bash
cp \
  "$SAVED_BOA/analysis/day3-boa-combined-noh2-results.ipynb" \
  "$DAY3_DIR/"
```

The combined experiment is an alternative optimization design, and it's only
intended for demonstration purposes.


## Part 4: Run an example optimization

The example uses:

- `flnr`, an ordinary ELM PFT parameter (fraction of leaf nitrogen allocated to rubisco);
- an Alquimia methanogenesis rate;
- daily GPP RMSE as the objective; and
- daily methane-flux RMSE as a tracking metric.

It runs 15 one-year ELM trials covering 2012, with five initialization trials
and no more than three trials pending at once.

### Launch The BOA Experiment
Submit the BOA controller to Slurm:

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

Record `BOA_JOB_ID`. The controller runs BOA and submits separate child Slurm
jobs for ELM.

Check the controller:

```bash
squeue -j "$BOA_JOB_ID"
sacct -j "$BOA_JOB_ID" --format=JobID,JobName,State,ExitCode,Elapsed
```

The controller log records the experiment directory and progress:

```bash
export BOA_LOG="$BOA_LOG_DIR/boa-workshop-${BOA_JOB_ID}.out"
tail -n 50 "$BOA_LOG"
```

Once BOA has started, obtain and record the experiment directory:

```bash
export BOA_EXPERIMENT=$(
  sed -n 's/^Output Experiment Dir: //p' "$BOA_LOG" | tail -n 1
)
echo "$BOA_EXPERIMENT"
```

## Other topics

### Multiple Patches, Repositories, And Code

Read {doc}`../../user-guide/multiple-wetland-patches` for the current
two-patch setup, patch-resolved output, area weighting, and
limitations.

Read {doc}`repositories-and-code-map` for:

- the roles of the ELM-Wet-Redox, workbench, REDOX-PFLOTRAN, Alquimia,
  PFLOTRAN-interface, OLMT, and BOA repositories;
- the difference between shared workshop snapshots and active development
  branches;
- a future fork-and-branch contribution workflow; and
- the main source locations for inputs, runs, wetland hydrology, Alquimia,
  reaction networks, output analysis, and BOA.

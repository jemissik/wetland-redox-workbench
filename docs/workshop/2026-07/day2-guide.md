# Day 2: Analyze Output And Compare With Observations

Day 2 goals:

1. read and interpret ELM-Wet-Redox history output;
2. compare model results with observations.

The main example uses a completed LA2 simulation.

## Model outputs
The general output-file guide is {doc}`../../user-guide/model-outputs`.

## Prepare The Notebook Environment

Day 2 uses a conda environment containing the output-analysis tools and
workbench modules. The same environment also contains BOA for Day 3. In a
Cardinal terminal, load the shared software environment and activate its conda
environment:

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

import wetland_redox_workbench

print(f"Python: {Path(sys.executable).resolve()}")
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

(day2-model-observation-comparison)=
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

Day 3 continues from this comparison by using the same aligned data and metrics
in BOA. See {doc}`day3-guide`.

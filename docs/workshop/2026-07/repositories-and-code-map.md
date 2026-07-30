# Repositories, Git, And Code Map

The workshop uses several repositories because the scientific model, chemistry
solver interface, run tooling, analysis tools, and optimization system are
maintained separately. The shared workshop installation combines tested
snapshots of these components; it is not one monolithic source repository.

## Software Repositories

| Repository | Role |
| --- | --- |
| [wetland-redox-workbench](https://github.com/jemissik/wetland-redox-workbench) | Site-input generation, run workflows, output analysis, BOA wrapper, templates, and documentation |
| [ELM-Wet-Redox model](https://github.com/jemissik/ELM-wet-redox-dev/tree/workshop-2026-07) | E3SM/ELM source containing the wetland landunit, forcing, hydrology, and Alquimia coupling |
| [Two-wetland-patch development branch](https://github.com/jemissik/ELM-wet-redox-dev/tree/feature/two-wetland-patch) | Current two-patch model checkpoint at commit `de8aa1f880` |
| [BOA](https://github.com/madeline-scyphers/boa) | Bayesian optimization and analysis framework |

```{note}
The exact shared workshop build includes project development branches and
pinned snapshots that may be newer than the default branch of an upstream
repository. Use the version records in a case or run manifest when
reproducing a workshop simulation.
```


## Shared Snapshot Versus Source Checkout

The shared installation under:

```text
/fs/ess/PAS0409/e3sm/software/elm-wet-redox-2026-07
```

is read-only. It is the stable path for reproducing workshop
examples.

For code development, you would want to clone the repository into your own directory.

In a run-workflow YAML file:

- `paths.model_root` selects the ELM source tree and CIME case tools;
- `paths.executable_root` selects an existing compiled build.

Omit `executable_root` after changing ELM source or switching to a branch that
requires a different build. See {doc}`../../user-guide/running-the-model` for
the complete rules.


## Contribution workflow

A typical contribution path is:

1. Fork the public repository on GitHub.
2. Clone the personal fork.
3. Add the main project as an `upstream` remote.
4. Create a focused feature branch.
5. Make and test a small, related set of changes.
6. Commit those changes with a descriptive message.
7. Push the feature branch to the personal fork.
8. Open a pull request for review.

For example:

```bash
git clone https://github.com/YOUR-USERNAME/wetland-redox-workbench.git
cd wetland-redox-workbench
git remote add upstream https://github.com/jemissik/wetland-redox-workbench.git
git switch -c feature/describe-the-change

git status
git add PATHS-YOU-INTEND-TO-COMMIT
git commit -m "Describe the focused change"
git push -u origin feature/describe-the-change
```

## Workbench Code Map

Start in the workbench for reusable setup, analysis, and BOA behavior:

| Task | Main locations |
| --- | --- |
| Generate point-site domain and surface inputs | `scripts/create_point_site_inputs.py`, `src/wetland_redox_workbench/site_inputs.py` |
| Convert wetland forcing CSV files | `scripts/create_wetland_forcing.py` |
| Copy or edit ELM parameter files | `scripts/create_elm_parameter_file.py`, `elm_parameters.py` |
| Plan and submit spinup/transient stages | `scripts/run_elm_workflow.py`, `run_workflow.py`, `run_config.py`, and `templates/run-workflows/` |
| Read ELM output | `elm_output.py` |
| Load and align observations | `observations.py`, `comparison.py`, and `metric_data.py` |
| Reduce and plot model results | `data_reduction.py`, `reaction_summaries.py`, and `plotting.py` |
| Configure BOA trials | `templates/boa/` |
| Stage, launch, and poll BOA trials | `boa_wrapper.py`, `trial_launcher.py`, and `trial_status.py` |


## ELM-Wet-Redox Model Code Map

Start in the model repository when the scientific model behavior itself must
change:

| Area | Main locations under `components/elm/src/` |
| --- | --- |
| Wetland subgrid topology and patch creation | `main/elm_varpar.F90`, `main/subgridMod.F90`, `main/initGridCellsMod.F90` |
| Wetland and multi-patch namelist controls | `main/elm_varctl.F90`, `main/controlMod.F90` |
| Wetland water-level forcing and patch elevation offsets | `biogeophys/WetlandSurfWatElevation.F90` |
| Wetland soil/surface hydrology | `biogeophys/SoilHydrologyMod.F90` |
| PFT parameter loading | `main/pftvarcon.F90` |
| Photosynthesis and patch-specific `flnr` use | `biogeophys/PhotosynthesisMod.F90` |
| ELM-Alquimia state exchange, reactions, and methane coupling | `external_models/emi/src/em/alquimia/ExternalModelAlquimiaMod.F90` |
| Column-level state and history diagnostics | `data_types/ColumnDataType.F90` |
| Vector and gridded history-file behavior | `main/histFileMod.F90` |

ELM is a large model. Begin from a known variable, namelist option, history
field, or function and use a text search to follow where it is declared, read,
updated, and written.

## Chemistry Code

| Task | Repository and starting location |
| --- | --- |
| Change how ELM exchanges state with the chemistry solver | ELM `ExternalModelAlquimiaMod.F90` and the Alquimia interface |
| Change PFLOTRAN chemistry implementation exposed through Alquimia | PFLOTRAN ELM interface |

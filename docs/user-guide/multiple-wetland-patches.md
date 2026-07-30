# Multiple Wetland Patches

The current ELM-Wet-Redox development model can represent two wetland patches
inside one point-site grid cell. This is useful when a site contains wetland
areas with different vegetation, elevation, inundation, or other
eco-hydrological characteristics that should retain separate model state.


## Conceptual Structure

A two-patch point site still has:

- one grid cell;
- one wetland landunit;
- one domain file;
- one surface file;
- one wetland boundary-forcing file; and
- one reaction-network deck.

Within the wetland landunit, the model creates two columns and one
vegetated PFT on each column. Each column stores separate hydrologic,
biogeochemical, and Alquimia state. Both columns use the same atmospheric and
wetland boundary inputs. The water level is adjusted by any configured patch
elevation offset.

There is currently no explicit lateral exchange of water, solutes, or gases
between the two columns.

## Configuration

The current implementation is fixed at exactly two patches. Configure their
fractions and elevation offsets in an ELM namelist additions file:

```fortran
wetland_patch_fraction = 0.10, 0.90
wetland_patch_elevation_offset = 0.0, 0.10

hist_type1d_pertape = 'PFTS'
hist_dov2xy = .false.
```

Both fractions must be positive and must sum to one. The elevation offsets are
meters above the common surface datum used by the wetland water-level forcing.
For each patch:

```text
patch-relative water level =
    common forcing water level - patch elevation offset
```

In the example, patch 2 experiences a water level 0.10 m lower relative to its
local ground surface than patch 1.

Reference the namelist additions file from the run-workflow YAML:

```yaml
inputs:
  namelist_file: ${CONFIG_DIR}/two_patch_user_nl_elm.txt
```

The same namelist settings must be applied consistently to every stage in the
AD-spinup, final-spinup, and transient chain.

## Patch-Specific Vegetation Parameters

For the CN/RD configuration used by the  model, optional `flnr_1` and
`flnr_2` variables in the ELM parameter NetCDF file set the two wetland PFTs'
Rubisco-N allocation parameters.

- If both variables are present, patch 1 uses `flnr_1` and patch 2 uses
  `flnr_2`.
- If neither is present, both patches use the ordinary `flnr` value.
- A parameter file containing only one variable in the pair is rejected.

Note: ELM-Wet used the CNP/ECA photosynthesis pathway, which has corresponding
`vcmax_np1_1` and `vcmax_np1_2` variables. These are not interchangeable with
`flnr_1` and `flnr_2`; they belong to different photosynthesis formulations
and have different meanings.

The current reaction-network deck is shared. Each column uses that network but
evolves an independent chemical state.

## Starting And Continuing Runs

The two-patch model has additional active column and PFT entries compared with
a single-patch model. A single-patch ELM restart therefore cannot be used
directly as a two-patch restart.

Use a consistent two-patch model source, parameter file, namelist, and restart
lineage for all stages. Begin a new spinup chain when changing from
single-patch to two-patch topology.


## Patch-Resolved History Output

Normal gridded history output averages subgrid information before writing it.
To retain separate patch values, configure a PFT-vector history tape:

```fortran
hist_type1d_pertape = 'PFTS'
hist_dov2xy = .false.
```

The vector tape includes mapping variables such as:

| Variable | Meaning |
| --- | --- |
| `pfts1d_active` | Whether each PFT-vector position is active |
| `pfts1d_itype_lunit` | Landunit type associated with each PFT position |
| `pfts1d_itype_veg` | Vegetation type associated with each PFT position |
| `pfts1d_wtgcell` | PFT fraction of the grid cell |
| `cols1d_active` | Whether each column-vector position is active |
| `cols1d_itype_lunit` | Landunit type associated with each column position |
| `cols1d_wtgcell` | Column fraction of the grid cell |

Do not hard-code the vector positions. Discover the active wetland PFT and
column indices from these mapping variables.

### PFT Versus Column Variables

On the current PFT-vector tape, the output dimension is named `pft` even for
some fields whose native ELM source is a **column**. Select positions using the
source type of the field:

| Source type | Examples | Mapping to use |
| --- | --- | --- |
| PFT | `VCMAX25TOP`, `GPP`, `NPP`, `TLAI`, `TOTVEGC` | Active wetland indices from the `pfts1d_*` variables |
| Column | `H2OSFC_WET`, `ZWT`, `TOTSOMC`, `CH4FLUX_ALQUIMIA`, soil chemistry and reaction rates | Active wetland indices from the `cols1d_*` variables |

This distinction matters because the two sets of indices are not generally the
same.

### Area Weighting

Patch values stored on the vector tape are not pre-weighted. Keep them
separate when examining patch heterogeneity. To calculate a grid-cell or site
aggregate, use the patch fractions:

```python
site_value = (patch_values * patch_weights).sum("patch")
```

For a 0.10/0.90 case, an unweighted average would give the wrong site-level
result.


## Current Limitations

- The topology is fixed at exactly two wetland patches.
- Patch fractions and elevation offsets are static namelist values.
- There is no explicit lateral water, solute, or gas exchange.
- Patch-specific controls are limited to the implemented parameter pairs.

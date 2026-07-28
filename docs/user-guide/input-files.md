# Input Files

ELM-Wet-Redox site runs generally need the standard ELM input files plus any
wetland-specific boundary forcing files used by the selected model features.

## Surface File

The surface file describes static landunit, soil, vegetation, and geographic
properties. Point-site files are commonly extracted from a global ELM surface
dataset and then updated with defensible site measurements.

Important fields include:

- site latitude, longitude, and represented area;
- landunit fractions such as `PCT_WETLAND`;
- PFT fractions such as `PCT_NAT_PFT`;
- soil sand, clay, and organic-matter profiles

The workbench point-site generator retains values from the nearest valid
global surface cell, makes the output 100% wetland, and supports explicit soil
and overrides. Inheriting a value from the nearest gridcell
is a documented starting assumption, not a substitute for site data.

Wetland patch fractions are not currently read from the point-site surface
file. See {ref}`multiple-wetland-patches` for how the development
two-patch configuration divides one wetland landunit into separate columns.

## Domain File

The domain file defines the model grid location, vertices, active mask, land
fraction, and area. A one-site domain normally has dimensions `ni=1`, `nj=1`,
and `nv=4`.

The point-site generator centers a copy of the nearest active global domain
cell on the requested coordinates. It retains the source-cell area unless the
modeled physical area is supplied explicitly.

See {doc}`site-input-generation` for the reusable generator, configuration
format, supported overrides, validation steps, and current limitations. The
July 2026 workshop commands and known LA2 example are in
{doc}`../workshop/2026-07/day1-create-site-inputs`.

## Wetland Boundary Forcing File

Wetland water level and optional solute boundary concentrations can be read
from a separate time-varying forcing file.

The CSV converter creates regular no-leap `water_level(time, gridcell)` files
and rejects gaps, duplicate timestamps, and missing values. Water level is in
meters relative to the soil surface, positive upward. Commands and input
requirements are documented in {doc}`site-input-generation`.

## Parameter Files

ELM NetCDF parameter files contain model and PFT parameters. They are not
automatically site-specific. Start from a tested baseline and create a separate
copy only when a named experiment changes a parameter.

## PFLOTRAN/Alquimia Decks

The chemistry deck defines species, reactions, initial chemistry, and kinetic
parameters. A new coordinate does not by itself require a new deck.

Structural network changes can change the state represented in ELM restart
files. Use a compatible spinup after changing species or reaction topology.
See {doc}`reaction-network-configuration` for the generator and configuration
format.

(multiple-wetland-patches)=
## Multiple Wetland Patches

The current ELM-Wet-Redox development code has an initial
two-patch implementation.

A multiple-patch setup does not require separate domain or surface files for
each patch. The site still has one gridcell and one wetland landunit. The
multi-patch-capable model creates two wetland columns and one PFT on each
column. Each column stores separate hydrologic, biogeochemical, and Alquimia
chemistry state.

The current controls are:

| Patch choice | Where it is configured |
| --- | --- |
| Number and topology | Model source; the current development implementation is fixed at exactly two wetland patches |
| Area fractions | ELM namelist variable `wetland_patch_fraction` |
| Ground elevations | ELM namelist variable `wetland_patch_elevation_offset` |
| Water-level forcing | One shared wetland boundary-forcing file referenced to a common surface datum |
| CN/RD photosynthesis contrast | Optional paired `flnr_1` and `flnr_2` variables in the ELM parameter NetCDF |
| CNP/ECA photosynthesis contrast | Optional paired `vcmax_np1_1` and `vcmax_np1_2` variables in the ELM parameter NetCDF |
| Reaction network | One Alquimia/PFLOTRAN deck; each column evolves its own chemical state using that network |
| Patch-resolved history output | ELM history namelist settings, typically PFT-vector output |

### Namelist Configuration

Create a short namelist additions file, for example
`two_patch_user_nl_elm.txt`:

```fortran
wetland_patch_fraction = 0.10, 0.90
wetland_patch_elevation_offset = 0.0, 0.10
hist_type1d_pertape = 'PFTS'
hist_dov2xy = .false.
```

Both fractions must be positive and must sum to one. Elevation offsets are in
meters above the common reference surface used by the wetland water-level
forcing. For each patch:

```text
patch-relative water level =
    common forcing water level - patch elevation offset
```

In this example, patch 2 experiences a water level 0.10 m lower relative to its
local ground surface than patch 1.

Point a run-workflow configuration to the additions file:

```yaml
inputs:
  namelist_file: ${CONFIG_DIR}/two_patch_user_nl_elm.txt
```

The workflow passes this file to OLMT, which adds its contents to the ELM
namelist for every configured stage.

### Patch-Specific Parameters

For the workshop example, optional `flnr_1` and `flnr_2` arrays
allow the two wetland PFTs to use different photosynthesis parameters. The
parameter file must contain both variables or neither. When neither is
present, both patches use the ordinary `flnr` array.

This accomplishes a similar function to what `vcmax_np1_1` and `vcmax_np1_2` did in ELM-Wet (which used the CNP/ECA photosynthesis formulation).

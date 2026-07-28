# Site Data Checklist

This checklist separates data needed to set up an ELM-Wet-Redox site simulation
from observations that are useful for model evaluation, parameterization, and
BOA/objective-function examples.

## Part 1: Data Needed For Model Setup

These data help build the domain file, surface file, meteorological forcing,
wetland boundary forcing, chemistry forcing, initial conditions, and model
configuration.

For a new site, the main model files we eventually need to create, adapt, or
choose are:

- Domain file: gridcell location, area, mask, and land fraction.
- Surface file: static land, soil, vegetation, and wetland properties.
- Meteorological forcing: atmospheric driver data or selected forcing product.
- Wetland boundary forcing file: water level and optional solute boundary
  concentrations.
- Parameter file or parameter overrides: PFT, wetland, and biogeochemical
  parameters if site-specific changes are needed.
- PFLOTRAN/Alquimia input deck: reaction network, species, and rate parameters.
- Case configuration: namelist options, model source path, run period, and
  output variables.

### Site And Experiment Metadata

- Site name and location.
- Latitude and longitude for each modeled site, patch, mesocosm, or plot.
- Patch/vegetation types, for example Typha and Panicum.
- Treatment design:
  - control versus saltwater intrusion treatments
  - target salinity, for example 5 ppt
  - treatment duration, for example 3 days or 20 days
  - treatment start/end dates and times

### Spatial And Land-Surface Information

Needed to create or adapt ELM domain and surface files.

- Land cover or patch fractions.
- Vegetation type and dominant species.
- Soil profile information:
  - soil texture by depth, especially sand/silt/clay
  - bulk density
  - porosity if available
  - organic matter or soil organic carbon/nitrogen by depth
  - mineral versus organic soil classification
  - soil layer depths
  - rooting depth if available
- Any site-specific topography, microtopography, drainage, or water-level cap
  information.

### Domain File Inputs

The ELM domain file describes the model grid. For a one-site or small set of
point simulations, we can usually generate this from site metadata.


### Surface File Inputs

The ELM surface file describes static site properties. This is where a new site
can require more preparation than LA2 if no existing surface file is available.

High-priority inputs:

- Soil texture by depth: sand, silt, clay.
- Soil organic carbon and nitrogen by depth.
- Bulk density and porosity if available.
- Soil layer depths or sampling depths.
- Vegetation/patch type and fractional cover.


### Hydrology And Wetland Water Forcing

Needed for wetland water-level forcing and to interpret treatment hydrology.

- Surface water depth or water level.
- Inundation timing and duration.
- Treatment water additions or drainage events.
- Any estimates of inflow/outflow, residence time, or exchange.

For ELM-Wet-Redox water-level forcing, the current model expects:

```text
water_level(time, gridcell)
```

where `water_level` is in meters relative to the soil surface, with positive
values above the soil surface.

### Saltwater And Chemistry Boundary Forcing


Current active ELM-Wet-Redox solute forcing can use:

```text
bc_salinity(time, gridcell)   ppt
bc_DOM1(time, gridcell)       mol/m3 H2O
```

The model can derive chloride, sodium, and sulfate-related boundary conditions
from salinity in the current implementation. Direct forcing of oxygen, nitrate,
ammonium, DIC, alkalinity, and other species is a useful future target but is
not included in the current interface.

### PFLOTRAN/Alquimia And Reaction-Network Inputs

Needed to choose or modify the chemistry setup:

- Which reaction network should be used.
- Whether salinity, sulfate, DOM, or methylotrophic pathways are central to the
  experiment.
- Any measured or assumed values for reaction-network parameters.
- Saltwater treatment chemistry, especially sulfate and salinity composition.
- DOM concentration and DOM C:N if DOM forcing or DOC/DON budgets are used.
- Which variables should be considered targets for parameter fitting.


## Part 2: Data Useful For Evaluation And Parameterization

These data do not necessarily drive the model. They help evaluate model output,
build objective functions, tune parameters, and interpret mechanisms.

### Gas Fluxes

- CH4 flux.
- CO2 flux.
- Separation of diffusion, ebullition, and plant-mediated flux.
- Before/after saltwater intrusion anomalies.
- Flux response as a function of salinity change.

### Porewater And Soil Profiles

Useful for vertical model evaluation:

- Porewater CH4 by depth.
- Porewater CO2 or DIC by depth.
- Salinity or EC by depth.
- pH by depth.
- Redox potential by depth.
- DOC/DOM by depth.
- Sulfate, chloride, sodium, nitrate, ammonium, oxygen if available.


### Plant And Canopy Observations

Useful for interpreting patch differences:

- Stomatal conductance.
- Biomass.
- LAI if measured.
- NDVI, GNDVI, GRVI, or other drone-derived indices.
- Canopy height.
- Leaf area or allometric relationships if available.

### Microbial Data

Useful for interpretation, even if not directly assimilated into the current
model:

- Biodiversity/community data before and after saltwater intrusion.
- Interpretations about functional groups.

The model does not simulate named microbial taxa directly. Microbial
data may still help interpret which reaction pathways or parameter changes are
scientifically plausible.

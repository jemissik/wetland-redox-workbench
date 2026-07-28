# ELM-Wet-Redox

ELM-Wet-Redox is a research version of the Energy Exascale Earth System Model
Land Model (ELM) for studying wetland carbon cycling, methane emissions, and
redox biogeochemistry. It combines a wetland-specific representation of
vegetation and hydrology with a configurable chemical reaction network.

ELM-Wet-Redox is built upon two lines of ELM development:
- ELM-Wet (Yazbeck et al. 2025), which added the wetland landunit and hydrology
- ELM-PFLOTRAN (Sulman et al. 2024), which coupled ELM with PFLOTRAN biochemistry to incorporate simulation of redox processes

The model is intended to address questions such as:

- How do water level, soil saturation, and vegetation affect wetland carbon
  dioxide and methane fluxes?
- How do oxygen, sulfate, iron, pH, and other chemical conditions alter methane production?
- How might salinity or saltwater intrusion change wetland greenhouse-gas
  emissions?
- Why might different vegetation and hydrologic patches within one wetland
  respond differently to the same environmental forcing?



## What The Model Simulates

ELM is a land-surface model. It calculates exchanges of energy, water, carbon,
and other materials among the atmosphere, vegetation, surface water, soil, and
subsurface. Depending on the configuration, it represents processes including:

- incoming meteorological forcing and land-atmosphere exchanges;
- snow, surface water, infiltration, soil water, and water-table behavior;
- soil temperature;
- photosynthesis, plant respiration, carbon allocation, and vegetation state;
- soil organic carbon and nitrogen pools; and
- carbon dioxide and methane exchange with the atmosphere.

In a point-site ELM-Wet-Redox simulation, one model gridcell represents the
site. The gridcell contains a wetland landunit, soil columns, plant functional
types (PFTs), and vertically resolved soil layers. Site inputs describe the
location, land cover, vegetation, soil, forcing, and chemistry assumptions.

The standard ELM model does not explicitly represent every redox process.
ELM-Wet-Redox therefore bypasses ELM's standard methane model and instead uses
PFLOTRAN to simulate a reaction network. The exact processes present depend on
the selected network, but a network may include:

- aerobic organic-matter decomposition and respiration;
- fermentation and production of dissolved substrates;
- sulfate reduction and sulfide oxidation;
- iron reduction, iron oxidation, and mineral reactions;
- acetoclastic, hydrogenotrophic, or methylotrophic methanogenesis;
- methane oxidation using oxygen, sulfate, or iron; and
- aqueous speciation and pH response.

This flexibility is important: methane production is not controlled by a
single fixed equation. It emerges from the configured reaction pathways,
substrate availability, environmental conditions, and transport.

## How This Version Was Developed

### ELM-Wet

Yazbeck et al. (2025) developed ELM-Wet to improve the representation of
wetland heterogeneity and methane emissions in ELM. That work:

- activated a dedicated wetland landunit;
- represented multiple wetland eco-hydrological patches, each with its own
  vegetation and soil column;
- added controls for patch water levels and maximum inundation depth;
- allowed observed surface-water elevation to constrain wetland hydrology; and
- revised aerenchyma methane transport using measured vegetation conductance per leaf
  area.

ELM-Wet used ELM's existing methane biogeochemistry.

### ELM-PFLOTRAN Redox Coupling

Sulman et al. (2024) coupled ELM to PFLOTRAN through the Alquimia interface to
represent flexible soil redox reaction networks. That work:

- connected ELM land state and carbon cycling to PFLOTRAN chemistry;
- represented oxygen, iron, sulfur, carbon, nitrogen, methane, and mineral
  interactions;
- coupled soil organic-matter decomposition to aqueous redox reactions;
- represented vertical solute and gas movement and surface gas exchange; and
- tested tide- and salinity-driven behavior in freshwater and saltwater coastal
  wetlands.

This development provides the redox chemistry and methane-biogeochemistry
foundation used by ELM-Wet-Redox.

### ELM-Wet-Redox

The current project merges and extends those two development paths. It uses the
wetland landunit and wetland hydrology together with the ELM-PFLOTRAN/Alquimia
chemistry pathway. Work since the merge has included:

- improvements to the wetland water level forcing;
- adding optional salinity and solute boundary forcing (e.g., DOM);
- supporting updated reaction networks including methylated-carbon pools;
- adding aqueous concentration, reaction-rate, redox, and methane-transport
  diagnostics; and
- developing reusable tools for reaction-deck generation, point-site input
  generation, staged spinup, model-output analysis, and parameter optimization.

ELM-Wet-Redox is still under active development!

## ELM, Alquimia, And PFLOTRAN

The three names refer to different jobs in the coupled model.

| Component | Main responsibility |
| --- | --- |
| ELM | Advances the land surface, vegetation, soil physical state, hydrology, carbon and nitrogen state, transport, and model clock |
| Alquimia | Provides the interface and data structures used to exchange state and rates between ELM and PFLOTRAN chemistry |
| PFLOTRAN | Reads the chemistry deck and solves aqueous speciation, kinetic reactions, and mineral reactions for the coupled soil chemistry |

Alquimia is the coupling layer
that lets ELM call PFLOTRAN without embedding a particular reaction network
throughout the ELM source code.

A simplified coupled timestep is:

```text
meteorology + wetland boundary forcing + previous model state
                              |
                              v
       ELM updates land, vegetation, temperature, and water state
                              |
                              v
       ELM supplies layer state and biogeochemical information
                              |
                              v
             Alquimia translates the data exchange
                              |
                              v
       PFLOTRAN solves the configured reactions and chemistry
                              |
                              v
       updated chemical state and reaction rates return to ELM
                              |
                              v
        ELM advances transport, surface fluxes, and model output
```

## Model And Workflow Software


### Scientific Model Stack

| Software | Role |
| --- | --- |
| `elm-wet-redox` | ELM source, wetland landunit, Alquimia coupling, transport, and ELM history/restart output |
| PFLOTRAN ELM interface | PFLOTRAN version used as the coupled chemistry engine |
| Alquimia | Library that exposes PFLOTRAN chemistry to ELM |
| PETSc | Numerical and parallel-computing dependency used by PFLOTRAN |
| REDOX-PFLOTRAN chemistry tools | Reaction-network configurations and the generator used to create PFLOTRAN/Alquimia decks |

### Run And Analysis Tools

| Software | Role |
| --- | --- |
| CIME | Creates E3SM cases, records configuration, builds executables, and creates batch scripts |
| OLMT | Higher-level point-site tooling that supplies CIME options and prepares ELM site cases |
| Wetland Redox Workbench | Site-input generation, run-workflow tools, output and observation utilities, documentation, and ELM-Wet-Redox BOA wrapper |
| BOA | Bayesian-optimization system that proposes parameter trials and tracks their results |


## From Site Data To Results

The complete workflow can be summarized as:

```text
site location and properties
        +
meteorological and wetland forcing
        +
ELM parameters and PFLOTRAN reaction network
        |
        v
domain, surface, forcing, parameter, and chemistry input files
        |
        v
CIME/OLMT case setup and model build
        |
        v
AD spinup -> final spinup -> transient or experiment
        |
        v
history files + restart files + logs
        |
        v
analysis, comparison with observations, and parameter optimization
```

Continue with:

- {doc}`input-files` for the main model inputs;
- {doc}`site-input-generation` for creating point-site inputs;
- {doc}`launch-tools` and {doc}`running-the-model` for running cases; and
- {doc}`model-outputs` for history files, restart files, and logs.

## Further Reading

- Yazbeck, T., et al. (2025). *ELM-Wet: Inclusion of a Wet-Landunit With
  Sub-Grid Representation of Eco-Hydrological Patches and Hydrological Forcing
  Improves Methane Emission Estimations in the E3SM Land Model (ELM)*.
  [doi:10.1029/2024MS004396](https://doi.org/10.1029/2024MS004396)
- Sulman, B. N., et al. (2024). *Integrating Tide-Driven Wetland Soil Redox and
  Biogeochemical Interactions Into a Land Surface Model*.
  [doi:10.1029/2023MS004002](https://doi.org/10.1029/2023MS004002)

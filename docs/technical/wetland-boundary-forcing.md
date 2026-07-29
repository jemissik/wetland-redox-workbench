# Wetland Boundary Forcing

ELM-Wet-Redox can prescribe wetland water level from a separate time-varying
boundary forcing file.

The wetland boundary forcing file should describe observed or scenario time
series, such as water level and optional solute boundary concentrations.

## Water Level Forcing

Current water-level forcing is enabled with:

```fortran
use_wetland_boundary_forcing = .true.
wetland_boundary_forcing_file = '/path/to/wetland_boundary_forcing.nc'
```

An optional water-level cap can be set:

```fortran
wetland_forcing_water_level_cap = 1.2
```

The cap is in meters. The default value is negative, which disables the cap, so
this option does not need to be specified unless a site-specific cap is desired.

### Required NetCDF Structure

The current required forcing variable is:

```text
water_level(time, gridcell)
```

`water_level` must be in meters relative to the soil surface, with positive
values above the soil surface. Internally, ELM stores the forced wetland surface
water value in `H2OSFC_WET` in millimeters.

A simple one-site forcing file should include:

```text
dimensions:
  time
  gridcell = 1
  scalar = 1
  nchar

variables:
  time(time)
  start_year(scalar)
  end_year(scalar)
  time_resolution_days(scalar)
  gridcell(gridcell)
  lat(gridcell)
  lon(gridcell)
  site_name(gridcell, nchar)
  water_level(time, gridcell)
```

The `gridcell` dimension can currently be either length 1, which broadcasts the
same forcing to the active site, or the same length as the model domain.

Wetland forcing files use regular no-leap records. Daily forcing uses
`time_resolution_days = 1.0`; hourly forcing uses `1/24`; half-hourly forcing
uses `1/48`. The `time` coordinate should use `calendar = "noleap"` and
fractional days for sub-daily records.

The model indexes wetland forcing using the same broad convention as ELM
meteorological forcing: regular no-leap records, model-calendar timing, and
year cycling when the model year falls outside the forcing-year range.

```text
model year inside start_year:end_year:
  use the matching forcing year

model year outside start_year:end_year:
  cycle through the available forcing years
```

This means a one-year forcing file can be used as a repeating spinup cycle, and
a multi-year forcing file can be calendar-aligned during matching transient
years.

Water level is applied as a stepwise state. ELM-Wet-Redox does not interpolate
between wetland forcing records; if interpolation or gap filling is needed, do
that when preparing the NetCDF forcing file.

## Creating Forcing Files

The workbench CSV converter reads a timestamp column and a water-level column,
accepts water levels in either meters or millimeters, drops leap days by
default, validates complete regular no-leap years, and writes `water_level` in
meters. It can write daily or sub-daily forcing if the input timestamps are
already on the requested regular interval.

```bash
python scripts/create_wetland_forcing.py \
  --csv water_level.csv \
  --time-column time \
  --water-level-column water_level \
  --water-level-units m \
  --site-name US-LA2 \
  --lat 29.8587 \
  --lon 269.7131 \
  --output wetland_boundary_forcing_US_LA2_waterlevel.nc
```

Optional `--salinity-column` and `--dom1-column` arguments add `bc_salinity`
and `bc_DOM1` on the same validated time axis. Salinity input is in `ppt`.
DOM1 input may use `mol/m3`, `mmol/L`, `mg-C/L`, or `g-C/m3`; carbon-mass
input is converted assuming one mole of carbon per mole of DOM1.

That conversion does not establish that measured total DOC is chemically
equivalent to the model's reactive DOM1 pool. Using a DOC observation column
as DOM1 also adopts the active reaction network's DOM1 reactivity and C:N
bookkeeping.

## Solute Forcing

The implemented solute-forcing mode supports salinity-derived boundary species
and DOM1 boundary concentrations in the wetland boundary forcing file.

Enable it with:

```fortran
use_wetland_boundary_forcing = .true.
use_wetland_solute_forcing = .true.
wetland_boundary_forcing_file = '/path/to/wetland_boundary_forcing_SITE.nc'
```

Then turn on the species to force:

```fortran
wetland_solute_force_salinity = .true.
wetland_solute_force_sulfate_from_salinity = .true.
wetland_solute_force_sulfide_from_salinity = .false.
wetland_solute_force_ph_from_salinity = .false.
wetland_solute_force_dom1 = .true.
wetland_solute_exchange_timescale_hours = 0.5
```

The main species flags are independent. For example, a salinity-only run can set
`wetland_solute_force_salinity = .true.` and
`wetland_solute_force_dom1 = .false.` even if the forcing file also contains a
DOM1 variable. If a species flag is true, the corresponding NetCDF variable is
required.

The salinity-derived switches use `bc_salinity`; they do not require separate
NetCDF variables for sulfate, sulfide, or pH. With
`wetland_solute_force_salinity = .true.`, chloride is required because it is the
primary species used to represent salinity, and `Na+` is also forced when it is
present in the active Alquimia network. Sulfate defaults on for salinity forcing,
while sulfide and pH/H+ default off.

Current solute forcing variables are:

```text
bc_salinity(time, gridcell)   ppt
bc_DOM1(time, gridcell)       mol/m3 H2O
```

`bc_salinity` is converted to the Alquimia chloride primary species using the
same salinity-to-chloride relationship used in the marsh/tidal code. The same
salinity input can also derive available `Na+`, optional `SO4--`, optional
`H2S(aq)`, and optional pH-derived `H+`. The newer REDOX-PFLOTRAN network uses
`H2S(aq)` as the primary sulfide boundary species, with `HS-` handled as a
secondary equilibrium species. The pH approximation follows Ben's marsh code
convention:

```text
pH = 6 + 2 * bc_salinity / 30
H+ = 1000 * 10**(-pH)    mol/m3 H2O
```

DOM1 is passed as a water concentration in mol/m3 H2O and mapped to the
Alquimia `DOM1` primary species.

The current mode only acts on the top Alquimia soil layer, and only when the
wetland boundary forcing has produced ponded wetland water:

```text
H2OSFC_WET > 0
```

The exchange follows a first-order concentration relaxation:

```text
C_new = C_old + (1 - exp(-dt/tau)) * (C_boundary - C_old)
```

where `tau` is `wetland_solute_exchange_timescale_hours`. Small values, such as
0.5 hours, make the top layer approach the boundary concentration rapidly. This
is equivalent to an implied exchange flux:

```text
Q_implied = V / tau
```

where `V` is the top-layer liquid pore volume represented by the exchange.

Current diagnostics include:

```text
WET_BC_SALINITY       prescribed salinity boundary concentration, ppt
WET_BC_DOM1           prescribed DOM1 boundary concentration, mol/m3 H2O
WET_CL_EXCHANGE       chloride exchange flux, mol/m2/s, positive into soil
WET_DOM1_EXCHANGE     DOM1 exchange flux, mol/m2/s, positive into soil
WET_NA_EXCHANGE       sodium exchange flux, mol/m2/s, positive into soil
WET_SO4_EXCHANGE      sulfate exchange flux, mol/m2/s, positive into soil
WET_H2S_EXCHANGE      H2S exchange flux, mol/m2/s, positive into soil
WET_HPLUS_EXCHANGE    H+ exchange flux, mol/m2/s, positive into soil
WET_BC_PH             salinity-derived pH boundary diagnostic
WET_BC_HPLUS          salinity-derived H+ boundary concentration, mol/m3 H2O
WET_SOLUTE_QIMPLIED   implied exchange water flux, mm/s
soil_salinity         diagnosed soil salinity from transported chloride, ppt
DOC_vr                vertically resolved dissolved organic carbon, gC/m3
```

DOM1 forcing changes the soil carbon and nitrogen inventory. Internally, the
DOM1 exchange is included in the existing Alquimia DOC/DON runoff bookkeeping
so the ELM C/N balance checks see it as an external dissolved C/N input or
removal. Positive `WET_DOM1_EXCHANGE` adds DOM1 to the soil and appears as
negative DOC/DON runoff under the existing runoff sign convention.

### DOM1 C:N Consistency

ELM maps Alquimia `DOM1` to both DOC and DON for diagnostics and C/N balance
bookkeeping. The DOM1 C:N mass ratio used by ELM is controlled by:

```fortran
alquimia_dom1_cn = 20.0
```

The default value, 20, matches the current generated LA2 H2S-primary
PFLOTRAN/Alquimia deck. This setting is a consistency parameter, not a free
calibration knob by itself: it must match the DOM1 C:N ratio and NH4 release
stoichiometry in the active PFLOTRAN reaction network. Changing
`alquimia_dom1_cn` without regenerating or editing the PFLOTRAN deck
consistently will generally break ELM nitrogen balance checks.

For a site-specific DOM C:N experiment, generate a matching PFLOTRAN deck from
the reaction-network source with the same `DOM_CN` value, then set
`alquimia_dom1_cn` to that value in `user_nl_elm`.

### Reaction-Network Compatibility

The current ELM solute-forcing bridge is aligned with the newer
REDOX-PFLOTRAN H2S-primary network. In that network, `H2S(aq)` is a mobile
primary species and `HS-` is a secondary equilibrium species. The older
Ben-paper deck used `HS-` as the mobile primary sulfide species. Because the
bridge now maps salinity-derived sulfide forcing, `WET_H2S_EXCHANGE`, and some
sulfate-reduction diagnostics to `H2S(aq)`, old-network support is not just a
deck-path change.


## Creating Forcing Files

The helper script `create_wetland_forcing.py` can be used to create forcing files.

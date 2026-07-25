# Model-Observation Comparison

The comparison tools prepare model and observation values for analysis or a
configured BOA metric. They make unit conversion, temporal aggregation,
timestamp alignment, and missing-data handling explicit.

Before comparing data:

- select a scalar model variable and normalize its interval timestamps;
- select the observation period and remove February 29 for an ELM comparison;
- document the source units, sign convention, and timestamp meaning; and
- decide the comparison frequency and required data coverage.

See {doc}`model-outputs` and {doc}`observation-data` for those preparation
steps.

## Convert Units And Signs

Model and observation values must use the same units and sign convention.
`apply_linear_conversion()` applies a configured scale and offset:

```python
from wetland_redox_workbench.comparison import apply_linear_conversion

observed_gpp = observations["GPP_PI_F"].copy()
observed_gpp.attrs["units"] = "umol CO2 m-2 s-1"

observed_gpp = apply_linear_conversion(
    observed_gpp,
    scale=-12.011e-6,
    target_units="gC/m^2/s",
    name="GPP",
)
```

This example converts GPP observations with units of umol CO2 m-2 s-1 (negative values = carbon uptake) to gC/m^2/s (where positive values = carbon uptake). Conversion factors must be specified by the user. The returned series records the operation in
`conversion_history`.

## Aggregate Model Output

Aggregate a one-dimensional model time series to the selected comparison
frequency:

```python
from wetland_redox_workbench.comparison import aggregate_model_timeseries

daily_model = aggregate_model_timeseries(
    model_gpp,
    frequency="1D",
    method="mean",
)
```

Model aggregation uses xarray's calendar-aware resampling. The default
`skipna=False` is strict: a missing model value makes the aggregate missing
instead of hiding potentially incomplete model output. The returned array
records the operation in `aggregation_history`.

Aggregate observations separately with the coverage rules described in
{doc}`observation-data`.

## Align By Timestamp

Align model and observation values by matching timestamps:

```python
from wetland_redox_workbench.comparison import align_model_observations

aligned = align_model_observations(
    daily_model,
    daily_observations["GPP"],
    min_pairs=30,
)
```

The result contains `model` and `observation` columns on a sorted pandas
datetime index. Alignment uses an inner timestamp join, not row position.
Missing pairs are dropped by default, and the function fails if fewer than
`min_pairs` valid pairs remain.

ELM no-leap dates are converted to pandas timestamps only after model
aggregation. Observation preparation removes February 29 so the calendars can
be matched by date.

Residuals are derived rather than stored:

```python
residual = aligned["model"] - aligned["observation"]
```

## Summarize The Comparison

Generate general diagnostics from the aligned table:

```python
from wetland_redox_workbench.comparison import summarize_comparison

summary = summarize_comparison(aligned)
print(summary)
```

The summary includes:

| Field | Meaning |
| --- | --- |
| `paired_count` | Number of valid model-observation pairs |
| `start_time`, `end_time` | Time range represented by valid pairs |
| `model_mean`, `model_min`, `model_max` | Model value summary |
| `observation_mean`, `observation_min`, `observation_max` | Observation value summary |
| `bias` | Mean of model minus observation |
| `mean_absolute_error` | Mean absolute model-observation difference |
| `rmse` | Root mean squared model-observation difference |
| `correlation` | Pearson correlation, when both series vary |

These values are analysis diagnostics. A BOA objective or tracking metric is
defined separately in the BOA configuration and receives the aligned model and
observation values.

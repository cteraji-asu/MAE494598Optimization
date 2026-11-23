# Generated two-PINN numerical summary

**Experiment A — hard routing between two networks** **[frozen 10 Nov run]**

| Model | Seed | Reflection error p95 | Median field $L_2$ error (%) | Feasible retained | False feasible | Design-gradient error (%) | Gate |
|---|---|---|---|---|---|---|---|
| monolithic | 0 | 1.49 | 5.48 | 0/24 | 0 | 95.5 | **FAIL** |
| two specialists | 0 | 1.09 | 4.17 | 2/24 | 0 | 85.6 | **FAIL** |
| monolithic | 1 | 1.48 | 4.61 | 7/24 | 0 | 95.6 | **FAIL** |
| two specialists | 1 | 1.14 | 3.87 | 10/24 | 0 | 89 | **FAIL** |
| monolithic | 2 | 1.41 | 4.53 | 0/24 | 0 | 95.1 | **FAIL** |
| two specialists | 2 | 1.17 | 4.46 | 0/24 | 0 | 90.7 | **FAIL** |

**Experiment B — differentiable (smooth) blending** **[frozen 10 Nov run]**

| Model | Seed | Reflection error p95 | Median field $L_2$ error (%) | Feasible retained | False feasible | Design-gradient error (%) | Gate |
|---|---|---|---|---|---|---|---|
| monolithic | 0 | 1.47 | 5.06 | 12/23 | 0 | 95 | **FAIL** |
| smooth specialists | 0 | 1.09 | 3.93 | 12/23 | 0 | 109 | **FAIL** |
| monolithic | 1 | 1.47 | 3.9 | 13/23 | 0 | 94.9 | **FAIL** |
| smooth specialists | 1 | 1.13 | 4.15 | 13/23 | 0 | 108 | **FAIL** |
| monolithic | 2 | 1.44 | 4.49 | 16/23 | 3 | 95 | **FAIL** |
| smooth specialists | 2 | 1.15 | 4.79 | 12/23 | 0 | 106 | **FAIL** |

Source: assets/two-pinn-results.json and assets/smooth-pinn-results.json.

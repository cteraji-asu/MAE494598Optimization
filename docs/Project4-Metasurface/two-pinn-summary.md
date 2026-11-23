# Generated two-PINN numerical summary

### Experiment A: hard parameter routing

| Model | Seed | Reflection error p95 | Median field L2 error (%) | Feasible retained | False feasible | Gradient error (%) | Gate |
|---|---|---|---|---|---|---|---|
| monolithic | 0 | 1.49082 | 5.48472 | 0/24 | 0 | 95.5437 | FAIL |
| two_specialists | 0 | 1.09076 | 4.17138 | 2/24 | 0 | 85.628 | FAIL |
| monolithic | 1 | 1.47565 | 4.60527 | 7/24 | 0 | 95.6212 | FAIL |
| two_specialists | 1 | 1.14034 | 3.86779 | 10/24 | 0 | 89.0482 | FAIL |
| monolithic | 2 | 1.41124 | 4.53248 | 0/24 | 0 | 95.1478 | FAIL |
| two_specialists | 2 | 1.17304 | 4.45794 | 0/24 | 0 | 90.7479 | FAIL |


### Experiment B: differentiable overlap

| Model | Seed | Reflection error p95 | Median field L2 error (%) | Feasible retained | False feasible | Gradient error (%) | Gate |
|---|---|---|---|---|---|---|---|
| monolithic | 0 | 1.47221 | 5.05793 | 12/23 | 0 | 95.0311 | FAIL |
| smooth_specialists | 0 | 1.0913 | 3.93036 | 12/23 | 0 | 109.295 | FAIL |
| monolithic | 1 | 1.47354 | 3.90167 | 13/23 | 0 | 94.9005 | FAIL |
| smooth_specialists | 1 | 1.12644 | 4.15216 | 13/23 | 0 | 107.77 | FAIL |
| monolithic | 2 | 1.44183 | 4.4931 | 16/23 | 3 | 95.0111 | FAIL |
| smooth_specialists | 2 | 1.14553 | 4.7922 | 12/23 | 0 | 105.91 | FAIL |


Each experiment has its own frozen cohort. Compare arms within an experiment, not raw counts across experiments. Source: assets/two-pinn-results.json and assets/smooth-pinn-results.json.

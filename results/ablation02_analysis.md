# Analysis: ablation02

## Resolution by condition
| condition | n | resolved | applying | >=Q2 | resolution_rate |
|---|---|---|---|---|---|
| C0_minimal | 12 | 5 | 10 | 5 | 0.42 |
| C1_context | 12 | 6 | 11 | 6 | 0.50 |
| C2_tests | 12 | 8 | 11 | 8 | 0.67 |
| C3_gates | 12 | 7 | 11 | 7 | 0.58 |
| C4_harness | 12 | 7 | 9 | 7 | 0.58 |
| C5_memory | 12 | 8 | 12 | 8 | 0.67 |
| C6_full_stack | 12 | 4 | 7 | 4 | 0.33 |

## Paired contrasts vs C0_minimal
| condition | n_pairs | Δresolve | 95% CI | b(only treat) | c(only base) | McNemar p |
|---|---|---|---|---|---|---|
| C1_context | 12 | +0.08 | [+0.00, +0.25] | 1 | 0 | 1.000 |
| C2_tests | 12 | +0.25 | [+0.00, +0.50] | 3 | 0 | 0.250 |
| C3_gates | 12 | +0.17 | [+0.00, +0.42] | 2 | 0 | 0.500 |
| C4_harness | 12 | +0.17 | [-0.17, +0.50] | 3 | 1 | 0.625 |
| C5_memory | 12 | +0.25 | [+0.00, +0.50] | 3 | 0 | 0.250 |
| C6_full_stack | 12 | -0.08 | [-0.42, +0.25] | 2 | 3 | 1.000 |

## Caveats
- small cohort (n=12/condition): directional only, no stats claim

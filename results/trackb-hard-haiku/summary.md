# Track B: trackb-hard-haiku

Model `claude-haiku-5-5`; 50 tasks with a finished session in every arm. Means with 95% bootstrap CIs (B = 1000, seed 42); cost over successful sessions. total_tokens counts input, output and cache read and write tokens as reported by the session; cost_usd is the session's own list-price cost. Tool used: sessions that ran the arm's tool at least once (where collected); Blocked: sessions with a call blocked by the permission check.

## Sessions per arm

| Arm | Records | OK | Cost USD | Missing task indices (0-based, sample order) |
|---|---|---|---|---|
| baseline | 50/50 | 50 | 0.20 | none |
| semble | 50/50 | 50 | 0.27 | none |
| graphify | 50/50 | 50 | 0.25 | none |

## Results on tasks finished in every arm

| Arm | Done | Tool used | Blocked | file_recall@1 | file_recall@5 | file_recall@10 | mrr | span_recall | span_precision | total_tokens | output_tokens | num_turns | duration_s | cost_usd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 50/50 | n/a | 0 | 0.179 [0.150, 0.207] | 0.438 [0.367, 0.506] | 0.459 [0.386, 0.525] | 0.880 [0.790, 0.960] | 0.289 [0.239, 0.343] | 0.562 [0.480, 0.651] | 86,464 [70,375, 105,930] | 2,220 [1,881, 2,604] | 5 [4, 5] | 17 [14, 19] | 0.004 [0.004, 0.005] |
| semble | 50/50 | 50/50 | 0 | 0.177 [0.147, 0.205] | 0.465 [0.392, 0.540] | 0.498 [0.421, 0.575] | 0.863 [0.763, 0.950] | 0.293 [0.240, 0.346] | 0.547 [0.463, 0.633] | 106,359 [90,938, 123,917] | 2,710 [2,299, 3,174] | 6 [5, 6] | 24 [21, 27] | 0.005 [0.005, 0.006] |
| graphify | 50/50 | 50/50 | 0 | 0.175 [0.144, 0.203] | 0.406 [0.338, 0.475] | 0.441 [0.365, 0.511] | 0.860 [0.760, 0.940] | 0.297 [0.248, 0.343] | 0.557 [0.469, 0.646] | 100,454 [87,323, 116,355] | 2,552 [2,226, 2,925] | 6 [5, 6] | 21 [19, 23] | 0.005 [0.005, 0.006] |

Paired bootstrap against `baseline`:

| Arm | Metric | Diff | 95% CI | p |
|---|---|---|---|---|
| semble | file_recall@1 | -0.002 | [-0.005, +0.000] | 0.700 |
| semble | file_recall@5 | +0.027 | [-0.005, +0.058] | 0.092 |
| semble | file_recall@10 | +0.039 | [+0.003, +0.074] | 0.036 |
| semble | mrr | -0.017 | [-0.050, +0.000] | 0.700 |
| semble | span_recall | +0.004 | [-0.035, +0.038] | 0.864 |
| semble | span_precision | -0.015 | [-0.078, +0.042] | 0.674 |
| semble | total_tokens | +19895.600 | [+8406.828, +31602.563] | 0.000 |
| semble | cost_usd | +0.0014 | [+0.0010, +0.0017] | 0.000 |
| semble | duration_s | +7.742 | [+5.644, +10.204] | 0.000 |
| graphify | file_recall@1 | -0.004 | [-0.011, +0.000] | 0.220 |
| graphify | file_recall@5 | -0.032 | [-0.077, +0.006] | 0.100 |
| graphify | file_recall@10 | -0.018 | [-0.063, +0.024] | 0.408 |
| graphify | mrr | -0.020 | [-0.050, +0.000] | 0.220 |
| graphify | span_recall | +0.008 | [-0.026, +0.039] | 0.666 |
| graphify | span_precision | -0.006 | [-0.068, +0.050] | 0.886 |
| graphify | total_tokens | +13989.960 | [+3620.488, +23844.398] | 0.004 |
| graphify | cost_usd | +0.0009 | [+0.0006, +0.0012] | 0.000 |
| graphify | duration_s | +4.382 | [+2.998, +5.840] | 0.000 |

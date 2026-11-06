# Track B: trackb-haiku

Model `claude-haiku-5-5`; 40 tasks with a finished session in every arm. Means with 95% bootstrap CIs (B = 1000, seed 42); cost over successful sessions. total_tokens counts input, output and cache read and write tokens as reported by the session; cost_usd is the session's own list-price cost. Tool used: sessions that ran the arm's tool at least once (where collected); Blocked: sessions with a call blocked by the permission check.

## Sessions per arm

| Arm | Records | OK | Cost USD | Missing task indices (0-based, sample order) |
|---|---|---|---|---|
| baseline | 50/100 | 50 | 0.37 | 50-99 |
| semble | 47/100 | 47 | 0.39 | 44, 48-99 |
| graphify | 40/100 | 40 | 0.41 | 35, 41-99 |

## Results on tasks finished in every arm

| Arm | Done | Tool used | Blocked | file_recall@1 | file_recall@5 | file_recall@10 | mrr | span_recall | span_precision | total_tokens | output_tokens | num_turns | duration_s | cost_usd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 40/40 | n/a | 0 | 0.632 [0.522, 0.737] | 0.817 [0.734, 0.885] | 0.830 [0.755, 0.893] | 0.988 [0.963, 1.000] | 0.459 [0.376, 0.545] | 0.623 [0.543, 0.705] | 273,638 [245,145, 302,841] | 1,826 [1,565, 2,101] | 6 [5, 7] | 13 [11, 14] | 0.007 [0.007, 0.008] |
| semble | 40/40 | 35/40 | 0 | 0.607 [0.495, 0.713] | 0.839 [0.754, 0.911] | 0.853 [0.771, 0.924] | 0.975 [0.938, 1.000] | 0.509 [0.444, 0.581] | 0.581 [0.490, 0.684] | 303,077 [275,167, 337,755] | 2,285 [1,944, 2,647] | 6 [5, 7] | 32 [29, 35] | 0.008 [0.008, 0.009] |
| graphify | 40/40 | 34/40 | 0 | 0.607 [0.495, 0.713] | 0.825 [0.744, 0.900] | 0.842 [0.765, 0.912] | 0.975 [0.938, 1.000] | 0.516 [0.442, 0.588] | 0.586 [0.501, 0.672] | 331,954 [292,019, 376,007] | 2,534 [2,113, 2,969] | 6 [5, 7] | 60 [49, 72] | 0.010 [0.009, 0.011] |

Paired bootstrap against `baseline`:

| Arm | Metric | Diff | 95% CI | p |
|---|---|---|---|---|
| semble | file_recall@1 | -0.025 | [-0.075, +0.000] | 0.758 |
| semble | file_recall@5 | +0.022 | [-0.031, +0.078] | 0.446 |
| semble | file_recall@10 | +0.024 | [-0.031, +0.080] | 0.386 |
| semble | mrr | -0.013 | [-0.037, +0.000] | 0.758 |
| semble | span_recall | +0.050 | [-0.018, +0.113] | 0.136 |
| semble | span_precision | -0.042 | [-0.113, +0.030] | 0.270 |
| semble | total_tokens | +29439.175 | [-2709.682, +63003.448] | 0.090 |
| semble | cost_usd | +0.0008 | [+0.0002, +0.0015] | 0.004 |
| semble | duration_s | +19.512 | [+16.469, +22.753] | 0.000 |
| graphify | file_recall@1 | -0.025 | [-0.075, +0.000] | 0.758 |
| graphify | file_recall@5 | +0.008 | [-0.035, +0.050] | 0.736 |
| graphify | file_recall@10 | +0.012 | [-0.031, +0.056] | 0.562 |
| graphify | mrr | -0.013 | [-0.037, +0.000] | 0.758 |
| graphify | span_recall | +0.057 | [-0.002, +0.118] | 0.060 |
| graphify | span_precision | -0.037 | [-0.112, +0.041] | 0.352 |
| graphify | total_tokens | +58315.800 | [+16236.541, +100879.699] | 0.006 |
| graphify | cost_usd | +0.0029 | [+0.0019, +0.0039] | 0.000 |
| graphify | duration_s | +47.374 | [+36.578, +59.058] | 0.000 |

# Track B: trackb-haiku

Model `claude-haiku-5-5`; 25 tasks with a finished session in every arm. Means with 95% bootstrap CIs (B = 1000, seed 42); cost over successful sessions. total_tokens counts input, output and cache read and write tokens as reported by the session; cost_usd is the session's own list-price cost. Tool used: sessions that ran the arm's tool at least once (where collected); Blocked: sessions with a call blocked by the permission check.

| Arm | Done | Tool used | Blocked | file_recall@1 | file_recall@5 | file_recall@10 | mrr | span_recall | span_precision | total_tokens | output_tokens | num_turns | duration_s | cost_usd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 25/25 | n/a | 0 | 0.678 [0.543, 0.820] | 0.841 [0.750, 0.931] | 0.856 [0.766, 0.940] | 0.980 [0.940, 1.000] | 0.500 [0.394, 0.609] | 0.644 [0.538, 0.754] | 283,769 [243,936, 325,822] | 1,823 [1,489, 2,152] | 6 [5, 7] | 13 [11, 14] | 0.008 [0.007, 0.008] |
| semble | 25/25 | 22/25 | 0 | 0.638 [0.495, 0.793] | 0.876 [0.761, 0.971] | 0.888 [0.783, 0.980] | 0.960 [0.900, 1.000] | 0.538 [0.447, 0.633] | 0.617 [0.501, 0.745] | 293,585 [263,396, 326,853] | 2,167 [1,745, 2,604] | 5 [5, 6] | 31 [27, 35] | 0.008 [0.007, 0.009] |
| graphify | 25/25 | 24/25 | 0 | 0.638 [0.495, 0.793] | 0.831 [0.723, 0.932] | 0.843 [0.746, 0.940] | 0.960 [0.900, 1.000] | 0.521 [0.424, 0.628] | 0.559 [0.462, 0.666] | 349,283 [309,611, 390,763] | 2,688 [2,213, 3,177] | 7 [6, 8] | 62 [54, 73] | 0.009 [0.008, 0.010] |

Paired bootstrap against `baseline`:

| Arm | Metric | Diff | 95% CI | p |
|---|---|---|---|---|
| semble | file_recall@5 | +0.035 | [-0.050, +0.120] | 0.474 |
| semble | mrr | -0.020 | [-0.060, +0.000] | 0.776 |
| semble | total_tokens | +9816.040 | [-32785.849, +49124.661] | 0.640 |
| graphify | file_recall@5 | -0.010 | [-0.070, +0.060] | 0.868 |
| graphify | mrr | -0.020 | [-0.060, +0.000] | 0.776 |
| graphify | total_tokens | +65514.280 | [+12717.022, +113253.191] | 0.016 |

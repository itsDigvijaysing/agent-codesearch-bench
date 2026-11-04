# Track B: trackb-pilot

Model `claude-haiku-5-5`; 10 tasks with a finished session in every arm. Means with 95% bootstrap CIs (B = 1000, seed 42); cost over successful sessions. total_tokens counts input, output and cache read and write tokens as reported by the session; cost_usd is the session's own list-price cost. Tool used: sessions that ran the arm's tool at least once (where collected); Blocked: sessions with a call blocked by the permission check.

| Arm | Done | Tool used | Blocked | file_recall@1 | file_recall@5 | file_recall@10 | mrr | span_recall | span_precision | total_tokens | output_tokens | num_turns | duration_s | cost_usd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 10/10 | n/a | 0 | 0.650 [0.475, 0.850] | 0.700 [0.550, 0.850] | 0.700 [0.550, 0.850] | 1.000 [1.000, 1.000] | 0.398 [0.262, 0.562] | 0.710 [0.547, 0.870] | 253,769 [210,163, 299,266] | 1,482 [1,115, 1,867] | 5 [4, 6] | 11 [9, 13] | 0.007 [0.006, 0.008] |
| semble | 10/10 | 4/10 | 1 | 0.650 [0.475, 0.850] | 0.775 [0.625, 0.925] | 0.775 [0.625, 0.925] | 1.000 [1.000, 1.000] | 0.457 [0.285, 0.647] | 0.768 [0.605, 0.924] | 271,818 [219,991, 323,841] | 1,849 [1,456, 2,274] | 5 [4, 6] | 33 [27, 40] | 0.008 [0.007, 0.009] |

Paired bootstrap against `baseline`:

| Arm | Metric | Diff | 95% CI | p |
|---|---|---|---|---|
| semble | file_recall@5 | +0.075 | [+0.000, +0.175] | 0.224 |
| semble | mrr | +0.000 | [+0.000, +0.000] | 1.000 |
| semble | total_tokens | +18048.600 | [-18071.438, +56288.600] | 0.388 |

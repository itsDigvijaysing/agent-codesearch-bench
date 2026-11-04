# Results: hard

Dataset `Contextbench/ContextBench` (contextbench_verified) at revision `c2855792b006`; 21 tasks from `data/sample_hard.txt`; top_k=10. Means with 95% bootstrap CIs (B=1000, seed 42); failed tasks score zero on quality metrics; Empty counts successful queries that returned nothing. n/a: not applicable (span metrics need line spans; token-budget recall needs returned code). Cost metrics are over successful tasks.

## Retrieval quality

| Tool | Version | Fail | Empty | R@1 | R@5 | R@10 | P@10 | MRR | Span R | Span P | R@2k tok | R@8k tok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grep | ripgrep 14.1.0 | 0/21 | 1/21 | 0.052 [0.016, 0.097] | 0.098 [0.042, 0.152] | 0.135 [0.072, 0.200] | 0.076 [0.043, 0.114] | 0.327 [0.159, 0.495] | 0.050 [0.022, 0.079] | 0.038 [0.008, 0.086] | 0.011 [0.003, 0.021] | 0.034 [0.011, 0.058] |
| grep-distinct | ripgrep 14.1.0 | 0/21 | 1/21 | 0.060 [0.016, 0.108] | 0.098 [0.044, 0.155] | 0.151 [0.079, 0.233] | 0.090 [0.048, 0.143] | 0.317 [0.151, 0.492] | 0.055 [0.022, 0.095] | 0.046 [0.013, 0.092] | 0.021 [0.006, 0.040] | 0.035 [0.013, 0.059] |
| bm25 | bm25s 0.3.16 | 0/21 | 0/21 | 0.050 [0.015, 0.092] | 0.142 [0.071, 0.217] | 0.199 [0.105, 0.296] | 0.119 [0.067, 0.176] | 0.353 [0.178, 0.540] | 0.082 [0.040, 0.128] | 0.068 [0.030, 0.114] | 0.055 [0.021, 0.088] | 0.082 [0.040, 0.128] |
| semble | semble 0.7.2 | 0/21 | 0/21 | 0.073 [0.039, 0.111] | 0.197 [0.115, 0.286] | 0.311 [0.207, 0.421] | 0.176 [0.124, 0.238] | 0.572 [0.389, 0.761] | 0.040 [0.017, 0.070] | 0.075 [0.042, 0.114] | 0.040 [0.017, 0.070] | 0.040 [0.017, 0.070] |
| graphify | graphifyy 0.9.102 | 0/21 | 0/21 | 0.042 [0.015, 0.077] | 0.145 [0.082, 0.212] | 0.214 [0.134, 0.311] | 0.119 [0.076, 0.176] | 0.401 [0.243, 0.577] | n/a | n/a | n/a | n/a |
| code-review-graph | code-review-graph 2.3.9 | 0/21 | 17/21 | 0.010 [0.000, 0.029] | 0.019 [0.000, 0.057] | 0.019 [0.000, 0.057] | 0.010 [0.000, 0.029] | 0.048 [0.000, 0.143] | 0.004 [0.000, 0.012] | 0.036 [0.000, 0.107] | n/a | n/a |

## Cost

| Tool | Tokens | Query s | Build s | Index MiB | RSS MiB |
|---|---|---|---|---|---|
| grep | 15205 [9115, 22043] | 0.04 [0.03, 0.05] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 18 [17, 19] |
| grep-distinct | 11020 [6821, 16005] | 0.04 [0.03, 0.05] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 18 [17, 19] |
| bm25 | 5796 [4807, 7064] | 0.00 [0.00, 0.00] | 2.3 [1.7, 3.1] | 9.3 [7.2, 11.9] | 264 [204, 329] |
| semble | 2138 [1588, 2994] | 0.05 [0.03, 0.07] | 6.5 [4.4, 9.1] | 47.1 [30.7, 66.6] | 385 [296, 491] |
| graphify | 2339 [2006, 2716] | 2.46 [1.74, 3.32] | 38.7 [24.9, 55.9] | 53.5 [33.6, 75.6] | 548 [346, 803] |
| code-review-graph | 1374 [1052, 1729] | 0.23 [0.21, 0.25] | 16.4 [10.5, 23.6] | 361.5 [225.3, 519.9] | 303 [212, 410] |

## Paired bootstrap against `grep`

| Tool | Metric | Diff | 95% CI | p |
|---|---|---|---|---|
| grep-distinct | file_recall@10 | +0.016 | [-0.024, +0.061] | 0.444 |
| grep-distinct | mrr | -0.010 | [-0.144, +0.114] | 0.908 |
| grep-distinct | line_recall@8000tok | +0.001 | [-0.015, +0.017] | 0.924 |
| bm25 | file_recall@10 | +0.065 | [-0.023, +0.152] | 0.152 |
| bm25 | mrr | +0.026 | [-0.170, +0.217] | 0.768 |
| bm25 | line_recall@8000tok | +0.048 | [+0.008, +0.088] | 0.024 |
| semble | file_recall@10 | +0.176 | [+0.085, +0.277] | 0.000 |
| semble | mrr | +0.245 | [+0.015, +0.475] | 0.038 |
| semble | line_recall@8000tok | +0.006 | [-0.024, +0.034] | 0.624 |
| graphify | file_recall@10 | +0.079 | [-0.016, +0.198] | 0.110 |
| graphify | mrr | +0.074 | [-0.144, +0.306] | 0.520 |
| code-review-graph | file_recall@10 | -0.116 | [-0.176, -0.061] | 0.000 |
| code-review-graph | mrr | -0.279 | [-0.446, -0.132] | 0.000 |

## Failures

None.

## Tools not in this run

- `serena` (track_b): Agent-driven symbolic navigation, not free-text retrieval; evaluated in Track B.
- `claude-context` (planned): v2: needs a Milvus instance and an embedding API key.

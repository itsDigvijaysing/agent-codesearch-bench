# Results: v1

Dataset `Contextbench/ContextBench` (contextbench_verified) at revision `c2855792b006`; 100 tasks from `data/sample_v1.txt`; top_k=10. Means with 95% bootstrap CIs (B=1000, seed 42); failed tasks score zero on quality metrics; Empty counts successful queries that returned nothing. n/a: not applicable (span metrics need line spans; token-budget recall needs returned code). Cost metrics are over successful tasks.

## Retrieval quality

| Tool | Version | Fail | Empty | R@1 | R@5 | R@10 | P@10 | MRR | Span R | Span P | R@2k tok | R@8k tok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grep | ripgrep 14.1.0 | 0/100 | 9/100 | 0.093 [0.046, 0.150] | 0.231 [0.167, 0.305] | 0.330 [0.251, 0.412] | 0.076 [0.058, 0.095] | 0.260 [0.192, 0.332] | 0.163 [0.117, 0.214] | 0.026 [0.015, 0.039] | 0.035 [0.014, 0.064] | 0.077 [0.045, 0.115] |
| grep-distinct | ripgrep 14.1.0 | 0/100 | 9/100 | 0.165 [0.108, 0.229] | 0.358 [0.285, 0.438] | 0.438 [0.366, 0.522] | 0.100 [0.079, 0.125] | 0.433 [0.348, 0.520] | 0.210 [0.161, 0.266] | 0.035 [0.023, 0.049] | 0.094 [0.057, 0.135] | 0.154 [0.109, 0.202] |
| bm25 | bm25s 0.3.16 | 0/100 | 0/100 | 0.148 [0.094, 0.216] | 0.375 [0.297, 0.455] | 0.402 [0.327, 0.485] | 0.094 [0.076, 0.113] | 0.400 [0.327, 0.481] | 0.224 [0.169, 0.285] | 0.078 [0.058, 0.102] | 0.173 [0.123, 0.227] | 0.224 [0.169, 0.285] |
| semble | semble 0.7.2 | 0/100 | 0/100 | 0.251 [0.181, 0.326] | 0.490 [0.416, 0.574] | 0.620 [0.551, 0.695] | 0.136 [0.118, 0.156] | 0.588 [0.508, 0.665] | 0.110 [0.077, 0.145] | 0.070 [0.053, 0.089] | 0.096 [0.063, 0.129] | 0.110 [0.077, 0.145] |
| graphify | graphifyy 0.9.102 | 0/100 | 0/100 | 0.111 [0.068, 0.160] | 0.342 [0.273, 0.424] | 0.433 [0.360, 0.520] | 0.098 [0.082, 0.115] | 0.397 [0.324, 0.479] | n/a | n/a | n/a | n/a |
| code-review-graph | code-review-graph 2.3.9 | 0/100 | 65/100 | 0.072 [0.033, 0.115] | 0.115 [0.064, 0.171] | 0.130 [0.075, 0.188] | 0.024 [0.014, 0.035] | 0.145 [0.082, 0.213] | 0.077 [0.037, 0.119] | 0.054 [0.023, 0.090] | n/a | n/a |

## Cost

| Tool | Tokens | Query s | Build s | Index MiB | RSS MiB |
|---|---|---|---|---|---|
| grep | 49546 [34390, 68247] | 0.04 [0.04, 0.06] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 23 [20, 26] |
| grep-distinct | 31653 [22892, 43254] | 0.04 [0.03, 0.06] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 23 [20, 26] |
| bm25 | 4728 [4562, 4949] | 0.00 [0.00, 0.00] | 1.9 [1.7, 2.2] | 8.2 [7.2, 9.3] | 238 [214, 267] |
| semble | 3383 [2986, 3882] | 0.06 [0.04, 0.08] | 6.7 [5.7, 7.8] | 47.7 [40.1, 56.0] | 392 [350, 438] |
| graphify | 3076 [2826, 3369] | 2.80 [2.40, 3.22] | 40.0 [32.2, 47.9] | 98.2 [78.4, 118.2] | 1077 [876, 1300] |
| code-review-graph | 2199 [1960, 2452] | 0.22 [0.21, 0.23] | 23.8 [17.6, 30.9] | 450.6 [361.9, 539.7] | 364 [308, 420] |

## Paired bootstrap against `grep`

| Tool | Metric | Diff | 95% CI | p |
|---|---|---|---|---|
| grep-distinct | file_recall@10 | +0.108 | [+0.041, +0.183] | 0.004 |
| grep-distinct | mrr | +0.173 | [+0.105, +0.247] | 0.000 |
| grep-distinct | line_recall@8000tok | +0.077 | [+0.037, +0.120] | 0.000 |
| bm25 | file_recall@10 | +0.072 | [-0.013, +0.151] | 0.088 |
| bm25 | mrr | +0.140 | [+0.064, +0.215] | 0.000 |
| bm25 | line_recall@8000tok | +0.147 | [+0.093, +0.205] | 0.000 |
| semble | file_recall@10 | +0.290 | [+0.207, +0.376] | 0.000 |
| semble | mrr | +0.328 | [+0.250, +0.405] | 0.000 |
| semble | line_recall@8000tok | +0.033 | [-0.010, +0.076] | 0.122 |
| graphify | file_recall@10 | +0.103 | [+0.021, +0.195] | 0.016 |
| graphify | mrr | +0.137 | [+0.064, +0.216] | 0.002 |
| code-review-graph | file_recall@10 | -0.201 | [-0.296, -0.109] | 0.000 |
| code-review-graph | mrr | -0.115 | [-0.209, -0.021] | 0.024 |

## Failures

None.

## Tools not in this run

- `serena` (track_b): Agent-driven symbolic navigation, not free-text retrieval; evaluated in Track B.
- `claude-context` (planned): v2: needs a Milvus instance and an embedding API key.

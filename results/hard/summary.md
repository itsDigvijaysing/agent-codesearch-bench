# Results: hard

Dataset `Contextbench/ContextBench` (contextbench_verified) at revision `c2855792b006`; 50 tasks from `data/sample_hard.txt`; top_k=10. Means with 95% bootstrap CIs (B=1000, seed 42); failed tasks score zero on quality metrics; Empty counts successful queries that returned nothing. n/a: not applicable (span metrics need line spans; token-budget recall needs returned code). Cost metrics are over successful tasks.

## Retrieval quality

| Tool | Version | Fail | Empty | R@1 | R@5 | R@10 | P@10 | MRR | Span R | Span P | R@2k tok | R@8k tok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grep | ripgrep 14.1.0 | 0/50 | 4/50 | 0.031 [0.011, 0.055] | 0.069 [0.037, 0.104] | 0.116 [0.074, 0.159] | 0.062 [0.040, 0.084] | 0.212 [0.120, 0.311] | 0.055 [0.032, 0.079] | 0.030 [0.013, 0.053] | 0.016 [0.004, 0.032] | 0.040 [0.020, 0.061] |
| grep-distinct | ripgrep 14.1.0 | 0/50 | 4/50 | 0.059 [0.032, 0.089] | 0.101 [0.059, 0.146] | 0.153 [0.102, 0.205] | 0.082 [0.054, 0.110] | 0.317 [0.202, 0.432] | 0.075 [0.046, 0.107] | 0.041 [0.022, 0.065] | 0.040 [0.017, 0.064] | 0.051 [0.027, 0.077] |
| bm25 | bm25s 0.3.16 | 0/50 | 0/50 | 0.035 [0.016, 0.060] | 0.122 [0.068, 0.175] | 0.178 [0.103, 0.249] | 0.092 [0.058, 0.124] | 0.275 [0.163, 0.388] | 0.075 [0.045, 0.111] | 0.046 [0.025, 0.068] | 0.046 [0.021, 0.077] | 0.075 [0.045, 0.111] |
| semble | semble 0.7.2 | 0/50 | 0/50 | 0.059 [0.035, 0.084] | 0.189 [0.135, 0.242] | 0.285 [0.218, 0.354] | 0.148 [0.112, 0.182] | 0.474 [0.356, 0.590] | 0.052 [0.029, 0.078] | 0.073 [0.046, 0.102] | 0.052 [0.028, 0.078] | 0.052 [0.029, 0.078] |
| graphify | graphifyy 0.9.102 | 0/50 | 0/50 | 0.033 [0.015, 0.055] | 0.154 [0.107, 0.208] | 0.211 [0.154, 0.270] | 0.104 [0.078, 0.134] | 0.349 [0.255, 0.450] | n/a | n/a | n/a | n/a |
| code-review-graph | code-review-graph 2.3.9 | 0/50 | 31/50 | 0.024 [0.006, 0.046] | 0.051 [0.021, 0.086] | 0.051 [0.021, 0.086] | 0.022 [0.008, 0.038] | 0.122 [0.045, 0.210] | 0.032 [0.008, 0.066] | 0.040 [0.007, 0.088] | n/a | n/a |

## Cost

| Tool | Tokens | Query s | Build s | Index MiB | RSS MiB |
|---|---|---|---|---|---|
| grep | 16796 [11565, 22799] | 0.05 [0.04, 0.06] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 20 [18, 23] |
| grep-distinct | 12866 [8636, 17560] | 0.04 [0.03, 0.05] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 20 [18, 23] |
| bm25 | 5615 [4920, 6461] | 0.00 [0.00, 0.00] | 2.5 [2.0, 3.1] | 10.0 [8.1, 12.4] | 279 [231, 333] |
| semble | 2080 [1739, 2532] | 0.06 [0.04, 0.07] | 6.8 [5.3, 8.3] | 50.2 [38.1, 62.9] | 404 [339, 475] |
| graphify | 2399 [2173, 2665] | 2.66 [2.10, 3.27] | 41.5 [32.2, 51.2] | 62.2 [46.5, 78.5] | 627 [469, 805] |
| code-review-graph | 1794 [1536, 2075] | 0.22 [0.21, 0.23] | 17.5 [13.5, 21.7] | 370.0 [283.7, 459.6] | 311 [250, 373] |

## Paired bootstrap against `grep`

| Tool | Metric | Diff | 95% CI | p |
|---|---|---|---|---|
| grep-distinct | file_recall@10 | +0.036 | [+0.006, +0.070] | 0.010 |
| grep-distinct | mrr | +0.105 | [+0.014, +0.202] | 0.018 |
| grep-distinct | line_recall@8000tok | +0.011 | [+0.000, +0.024] | 0.050 |
| bm25 | file_recall@10 | +0.062 | [-0.009, +0.136] | 0.098 |
| bm25 | mrr | +0.063 | [-0.062, +0.190] | 0.332 |
| bm25 | line_recall@8000tok | +0.035 | [+0.000, +0.075] | 0.046 |
| semble | file_recall@10 | +0.169 | [+0.108, +0.235] | 0.000 |
| semble | mrr | +0.262 | [+0.138, +0.391] | 0.000 |
| semble | line_recall@8000tok | +0.013 | [-0.019, +0.042] | 0.376 |
| graphify | file_recall@10 | +0.095 | [+0.022, +0.167] | 0.004 |
| graphify | mrr | +0.137 | [-0.002, +0.268] | 0.056 |
| code-review-graph | file_recall@10 | -0.065 | [-0.110, -0.021] | 0.002 |
| code-review-graph | mrr | -0.090 | [-0.206, +0.032] | 0.156 |

## Failures

None.

## Tools not in this run

- `serena` (track_b): Agent-driven symbolic navigation, not free-text retrieval; evaluated in Track B.
- `claude-context` (planned): v2: needs a Milvus instance and an embedding API key.

# Results: v1

Dataset `Contextbench/ContextBench` (contextbench_verified) at revision `c2855792b006`; 100 tasks from `data/sample_v1.txt`; top_k=10. Means with 95% bootstrap CIs (B=1000, seed 42); failed tasks score zero on quality metrics. Cost metrics are over successful tasks.

## Retrieval quality

| Tool | Version | Fail | R@1 | R@5 | R@10 | P@10 | MRR | Span R | Span P | R@2k tok | R@8k tok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| grep | ripgrep 14.1.0 | 0/100 | 0.093 [0.046, 0.150] | 0.231 [0.167, 0.305] | 0.330 [0.251, 0.412] | 0.076 [0.058, 0.095] | 0.260 [0.192, 0.332] | 0.163 [0.117, 0.214] | 0.026 [0.015, 0.039] | 0.035 [0.014, 0.064] | 0.077 [0.045, 0.115] |
| grep-distinct | ripgrep 14.1.0 | 0/100 | 0.165 [0.108, 0.229] | 0.358 [0.285, 0.438] | 0.438 [0.366, 0.522] | 0.100 [0.079, 0.125] | 0.433 [0.348, 0.520] | 0.210 [0.161, 0.266] | 0.035 [0.023, 0.049] | 0.094 [0.057, 0.135] | 0.154 [0.109, 0.202] |
| bm25 | bm25s 0.3.16 | 0/100 | 0.148 [0.094, 0.216] | 0.375 [0.297, 0.455] | 0.402 [0.327, 0.485] | 0.094 [0.076, 0.113] | 0.400 [0.327, 0.481] | 0.224 [0.169, 0.285] | 0.078 [0.058, 0.102] | 0.173 [0.123, 0.227] | 0.224 [0.169, 0.285] |

## Cost

| Tool | Tokens | Query s | Build s | Index MiB | RSS MiB |
|---|---|---|---|---|---|
| grep | 49546 [34390, 68247] | 0.04 [0.04, 0.06] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 23 [20, 26] |
| grep-distinct | 31653 [22892, 43254] | 0.04 [0.03, 0.05] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 23 [20, 26] |
| bm25 | 4728 [4562, 4949] | 0.00 [0.00, 0.00] | 2.1 [1.8, 2.5] | 8.2 [7.2, 9.3] | 237 [213, 267] |

## Paired bootstrap against `grep`

| Tool | Metric | Diff | 95% CI | p |
|---|---|---|---|---|
| grep-distinct | file_recall@10 | +0.108 | [+0.041, +0.183] | 0.004 |
| grep-distinct | mrr | +0.173 | [+0.105, +0.247] | 0.000 |
| grep-distinct | line_recall@8000tok | +0.077 | [+0.037, +0.120] | 0.000 |
| bm25 | file_recall@10 | +0.072 | [-0.013, +0.151] | 0.088 |
| bm25 | mrr | +0.140 | [+0.064, +0.215] | 0.000 |
| bm25 | line_recall@8000tok | +0.147 | [+0.093, +0.205] | 0.000 |

## Failures

None.

## Tools not in this run

- `semble` (planned): M1: CLI `semble search <query> <repo> --top-k K` or Python API (SembleIndex).
- `graphify` (planned): M2: deterministic AST code mode only; excluded if retrieval needs an LLM.
- `code-review-graph` (planned): M2: included only if a query interface works without an LLM.
- `serena` (track_b): Agent-driven symbolic navigation, not free-text retrieval; evaluated in Track B.
- `claude-context` (planned): v2: needs a Milvus instance and an embedding API key.

# Results: v1

Dataset `Contextbench/ContextBench` (contextbench_verified) at revision `c2855792b006`; 10 tasks from `data/sample_v1.txt`; top_k=10. Means with 95% bootstrap CIs (B=1000, seed 42); failed tasks score zero on quality metrics. Cost metrics are over successful tasks.

## Retrieval quality

| Tool | Version | Fail | R@1 | R@5 | R@10 | P@10 | MRR | Span R | Span P | R@2k tok | R@8k tok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| grep | ripgrep 14.1.0 | 0/10 | 0.100 [0.000, 0.300] | 0.225 [0.050, 0.425] | 0.275 [0.075, 0.475] | 0.060 [0.020, 0.100] | 0.229 [0.058, 0.433] | 0.171 [0.057, 0.318] | 0.024 [0.002, 0.060] | 0.016 [0.000, 0.048] | 0.062 [0.000, 0.169] |
| bm25 | bm25s 0.3.16 | 0/10 | 0.250 [0.000, 0.500] | 0.475 [0.225, 0.725] | 0.475 [0.225, 0.725] | 0.070 [0.040, 0.100] | 0.428 [0.185, 0.674] | 0.293 [0.102, 0.496] | 0.086 [0.034, 0.154] | 0.220 [0.074, 0.391] | 0.293 [0.102, 0.496] |

## Cost

| Tool | Tokens | Query s | Build s | Index MiB | RSS MiB |
|---|---|---|---|---|---|
| grep | 100085 [50374, 162938] | 0.05 [0.04, 0.06] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 23 [20, 27] |
| bm25 | 4370 [3961, 4830] | 0.00 [0.00, 0.00] | 1.3 [0.6, 2.2] | 4.8 [2.4, 7.8] | 153 [100, 217] |

## Paired bootstrap against `grep`

| Tool | Metric | Diff | 95% CI | p |
|---|---|---|---|---|
| bm25 | file_recall@10 | +0.200 | [-0.050, +0.500] | 0.202 |
| bm25 | line_recall@8000tok | +0.231 | [+0.027, +0.459] | 0.016 |
| bm25 | mrr | +0.199 | [-0.042, +0.489] | 0.124 |

## Failures

None.

## Tools not in this run

- `semble` (planned): M1: CLI `semble search <query> <repo> --top-k K` or Python API (SembleIndex).
- `graphify` (planned): M2: deterministic AST code mode only; excluded if retrieval needs an LLM.
- `code-review-graph` (planned): M2: included only if a query interface works without an LLM.
- `serena` (track_b): Agent-driven symbolic navigation, not free-text retrieval; evaluated in Track B.
- `claude-context` (planned): v2: needs a Milvus instance and an embedding API key.

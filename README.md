# codesearch-bench

A neutral, reproducible benchmark for the code-search and code-context tools that coding agents
use. It measures how well each tool retrieves the code a task actually needs, and what that
costs in tokens, time and memory.

## Why

People keep asking for independent numbers, and tool authors say none exist:

- r/ClaudeAI, graphify launch thread: "Do you have benchmarks to show realistic expectations?"
  <https://www.reddit.com/r/ClaudeAI/comments/1ui6unv>
- r/ClaudeAI, semble launch thread: "would use a real benchmark not their own self
  validation"; semble's author replied: "None of the methods we benchmarked had any kind of
  decent benchmark." <https://www.reddit.com/r/ClaudeAI/comments/1szvo7t>

**Neutrality.** This project has no affiliation with any tool it evaluates. Every tool runs
with its documented interface and default settings first; tuned settings are labelled
separately. Maintainers can propose a configuration through a pull request (see
[CONTRIBUTING.md](CONTRIBUTING.md)).

## Results

Status: milestone M0 (smoke run on the first 10 sample tasks). The full 100-task table, with
more tools, comes in M1 and later. Current table: [results/v1/summary.md](results/v1/summary.md).

| Tool | File recall@10 | MRR | Line recall @ 8k tokens | Tokens returned | Failures |
|---|---|---|---|---|---|
| grep (ripgrep 14.1.0) | 0.275 [0.075, 0.475] | 0.229 [0.058, 0.433] | 0.062 [0.000, 0.169] | 100,085 | 0/10 |
| BM25 (bm25s 0.3.16) | 0.475 [0.225, 0.725] | 0.428 [0.185, 0.674] | 0.293 [0.102, 0.496] | 4,370 | 0/10 |

Means over 10 tasks with 95% bootstrap confidence intervals. With n = 10 the intervals are
wide; do not draw conclusions from this table.

## Method

**Dataset.** [ContextBench](https://github.com/EuniAI/ContextBench) (Apache-2.0,
[arXiv 2602.05892](https://arxiv.org/abs/2602.05892)), Hugging Face dataset
[`Contextbench/ContextBench`](https://huggingface.co/datasets/Contextbench/ContextBench),
config `contextbench_verified` (500 tasks with human-annotated gold context), pinned to
revision `c2855792b006af41c67202d33883fb9d46362853`. Gold context is a list of
`{file, start_line, end_line}` spans.

**v1 sample** ([`data/sample_v1.txt`](data/sample_v1.txt), rule in
[`src/csbench/sample.py`](src/csbench/sample.py)): Python tasks only; the 10 repositories
with the most Python tasks (ties by name); 100 tasks spread across them by water-filling
(equal quota per repository, repositories with fewer tasks give all of theirs, leftover seats
drawn with `random.Random(0)`); tasks inside each repository drawn with the same generator; the
list is then shuffled, so any prefix is also a seeded random subset. Result: django,
transformers, scikit-learn and matplotlib 10 each; sympy, ansible, sphinx and keras 11 each;
xarray and openlibrary 8 each.

**Input.** Each tool gets the task's issue text (problem statement) as the query, with the
repository checked out at the task's base commit. Each tool is asked for its top 10 results
in its own unit (files or chunks).

**Track A: retrieval only.** Each tool returns ranked context (files and, where available,
line spans), which is scored against the gold context. Track B (an agent using each tool,
measuring task success and tokens) is planned; see [PLAN.md](PLAN.md).

**Baselines.**
- *grep*: identifiers extracted from the issue text (file paths, dotted names, CamelCase and
  camelCase, snake_case, quoted strings of 3 to 80 characters; at most 64 terms) searched with
  ripgrep as fixed strings in one pass. Files are ranked by total hit count (ties: distinct
  terms matched, then path). Each file returns its hit lines with 3 lines of context. The rule
  is documented in [`adapters/grep.py`](src/csbench/adapters/grep.py).
- *BM25*: [bm25s](https://github.com/xhluca/bm25s) (Lucene variant, k1 = 1.5, b = 0.75) over
  50-line chunks of git-tracked text files up to 1 MB; code-aware tokenizer (snake_case and
  camelCase split, lowercased). See [`adapters/bm25.py`](src/csbench/adapters/bm25.py).

**Metrics per (tool, task).** Ranked files are the distinct files of the results in order.
- File recall@1/5/10, file precision@5/10 (divided by k), MRR of the first gold file.
- Span recall and precision: line-level overlap of the union of returned spans with the gold
  lines, using ContextBench's line-interval metric (ported in
  [`intervals.py`](src/csbench/intervals.py)). One deviation: an empty result has precision
  0, not 1.
- Tokens returned: the returned lines, read from the checkout, counted with tiktoken
  `o200k_base` (tool formatting overhead is excluded). A whole-file result counts the whole
  file.
- Line recall at 2,000 and 8,000 tokens: gold-line recall of the results taken in rank order
  until the budget is used; the result that crosses the budget keeps its leading lines.
- Query latency, index build time, index size on disk, and peak RSS (maximum over the worker
  process and its child processes). Each (tool, task) runs in a fresh worker process on CPU.

**Statistics.** Means with 95% percentile bootstrap confidence intervals over tasks
(B = 1000, seed 42), and a paired bootstrap of each tool against the grep baseline
(`results/<run>/paired_vs_grep.csv`). Failed tasks are never dropped: they score zero on every
quality metric and the failure rate is reported. Cost metrics are over successful tasks.

## Reproduce

Requires [uv](https://docs.astral.sh/uv/), git and ripgrep. One command reproduces every
number:

```bash
make all
```

This is `uv run csbench all --config configs/v1.yaml`: it downloads the pinned dataset,
checks out each task's repository (blobless clone plus a worktree), runs every active tool,
and writes `results/v1/`. Runs are resumable; per-task records are kept in
`results/v1/per_task/<tool>.jsonl.gz`. Versions are pinned in `uv.lock` and
[`configs/tools.yaml`](configs/tools.yaml).

## Tools

| Tool | Status |
|---|---|
| grep baseline, BM25 baseline | in v1 |
| [semble](https://github.com/MinishLab/semble) | M1 |
| [graphify](https://github.com/Graphify-Labs/graphify) | M2, deterministic AST code mode only |
| [code-review-graph](https://github.com/tirth8205/code-review-graph) | M2, only if it can be queried without an LLM |
| [Serena](https://github.com/oraios/serena) | Track B: agent-driven symbolic navigation, not free-text retrieval |
| [claude-context](https://github.com/zilliztech/claude-context) | v2: needs a Milvus instance and an embedding API key |

## Limitations

- Gold context is what human annotators judged necessary for one fix; other relevant code
  can exist, so precision is a lower bound.
- The issue text is used verbatim as a single query. Agents usually issue several, refined
  queries; Track B covers that.
- The v1 sample is Python only, from 10 repositories.
- Tokens count returned code only, not each tool's output formatting.

## Credits and license

Gold context, task data and the line-interval metric come from ContextBench (Apache-2.0).
This repository is licensed under the [Apache License 2.0](LICENSE).

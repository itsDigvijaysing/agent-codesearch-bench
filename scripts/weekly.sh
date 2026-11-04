#!/usr/bin/env bash
# Weekly refresh: upgrade the pinned versions of the tools under test, rerun what changed,
# and commit updated results when a version changed. Safe to run repeatedly: each call runs
# one batch of at most BATCH_MIN minutes and resumes where the previous call stopped.
#
# Exit codes: 0 done (results committed and pushed, or nothing changed);
#             3 batch stopped at its time limit, run the script again to continue;
#             4 an upgrade changed a tool default and needs review (nothing committed).
set -euo pipefail
cd "$(dirname "$0")/.."

CONFIG="${CONFIG:-configs/v1.yaml}"
BATCH_MIN="${BATCH_MIN:-25}"

git config user.name "itsdigvijaysing"
git config user.email "itsdigvijaysing@gmail.com"
git pull --ff-only origin main
uv sync --frozen

changes="$(uv run csbench upgrade --config "$CONFIG")"   # exits 4 when review is needed
if [ -n "$changes" ]; then
  echo "upgraded:"
  echo "$changes"
  git add configs/tools.yaml configs/envs
  git commit -m "build(tools): upgrade pinned tool versions"
fi

# Resumes pending (tool, task) pairs; only tools whose fingerprint changed are pending.
set +e
uv run csbench run --config "$CONFIG" --time-budget-min "$BATCH_MIN"
status=$?
set -e
if [ "$status" -eq 3 ]; then
  echo "batch stopped at ${BATCH_MIN} minutes; run scripts/weekly.sh again to continue"
  exit 3
elif [ "$status" -ne 0 ]; then
  exit "$status"
fi

uv run csbench report --config "$CONFIG"
git add results README.md
if git diff --cached --quiet; then
  echo "results unchanged"
else
  git commit -m "docs(results): refresh results after tool upgrades"
fi
if [ -n "$(git log origin/main..HEAD --oneline)" ]; then
  git push origin HEAD:main
fi

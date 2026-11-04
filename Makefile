CONFIG ?= configs/v1.yaml

.PHONY: all sync check sample run report

# Recompute every number from scratch (committed per-task records are ignored).
all: sync
	uv run csbench all --fresh --config $(CONFIG)

sync:
	uv sync --frozen

check:
	uv run ruff check .
	uv run pytest -q

sample:
	uv run csbench sample --config $(CONFIG)

# Resume a run, reusing records committed in results/ (used for batched runs).
run:
	uv run csbench run --config $(CONFIG)

report:
	uv run csbench report --config $(CONFIG)

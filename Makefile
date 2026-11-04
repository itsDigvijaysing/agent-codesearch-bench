CONFIG ?= configs/v1.yaml

.PHONY: all sync check sample run report

all: sync
	uv run csbench all --config $(CONFIG)

sync:
	uv sync --frozen

check:
	uv run ruff check .
	uv run pytest -q

sample:
	uv run csbench sample --config $(CONFIG)

run:
	uv run csbench run --config $(CONFIG)

report:
	uv run csbench report --config $(CONFIG)

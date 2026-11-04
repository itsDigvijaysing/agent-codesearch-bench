from csbench.adapters.base import Adapter, Hit


def get_adapter(name: str) -> type[Adapter]:
    if name == "grep":
        from csbench.adapters.grep import GrepAdapter

        return GrepAdapter
    if name == "bm25":
        from csbench.adapters.bm25 import BM25Adapter

        return BM25Adapter
    if name == "semble":
        from csbench.adapters.semble import SembleAdapter

        return SembleAdapter
    if name == "graphify":
        from csbench.adapters.graphify import GraphifyAdapter

        return GraphifyAdapter
    if name == "code-review-graph":
        from csbench.adapters.code_review_graph import CodeReviewGraphAdapter

        return CodeReviewGraphAdapter
    raise KeyError(f"unknown adapter: {name}")


__all__ = ["Adapter", "Hit", "get_adapter"]

import importlib

import pytest

PACKAGES = [
    "dispute_analyst",
    "dispute_analyst.domain",
    "dispute_analyst.features",
    "dispute_analyst.features.open_dispute",
    "dispute_analyst.features.analyze_dispute",
    "dispute_analyst.features.approve_decision",
    "dispute_analyst.features.execute_refund",
    "dispute_analyst.features.get_dispute",
    "dispute_analyst.features.list_queue",
    "dispute_analyst.projections",
    "dispute_analyst.agents",
    "dispute_analyst.knowledge",
    "dispute_analyst.ports",
    "dispute_analyst.adapters",
    "dispute_analyst.infra",
    "dispute_analyst.entrypoints",
]


@pytest.mark.parametrize("name", PACKAGES)
def test_package_imports(name: str) -> None:
    assert importlib.import_module(name).__name__ == name

"""The domain imports only the standard library and itself (see domain/AGENTS.md)."""

import ast
import sys
from pathlib import Path

import dispute_analyst.domain as domain

DOMAIN = "dispute_analyst.domain"


def _is_allowed(module: str) -> bool:
    top_level = module.split(".")[0]
    return (
        top_level in sys.stdlib_module_names or module == DOMAIN or module.startswith(f"{DOMAIN}.")
    )


def _imports(node: ast.AST) -> list[tuple[int, str]]:
    """(line, module) for each absolute import. Relative imports never leave the domain."""
    if isinstance(node, ast.Import):
        return [(node.lineno, alias.name) for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return [(node.lineno, node.module)]
    return []


def test_domain_imports_only_stdlib_and_itself() -> None:
    violations: list[str] = []

    for path in Path(domain.__file__).parent.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            violations += [
                f"{path}:{line} imports {module}"
                for line, module in _imports(node)
                if not _is_allowed(module)
            ]

    assert not violations, "\n".join(violations)
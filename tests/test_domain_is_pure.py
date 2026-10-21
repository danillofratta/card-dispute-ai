import ast
import sys
from pathlib import Path
import dispute_analyst.domain as domain


def test_domain_is_pure():
    domain_path = Path(domain.__file__).parent
    violations = []

    for path in domain_path.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod_name = alias.name
                    top_name = mod_name.split(".")[0]
                    
                    is_stdlib = top_name in sys.stdlib_module_names
                    is_domain = mod_name == "dispute_analyst.domain" or mod_name.startswith("dispute_analyst.domain.")
                    
                    if not (is_stdlib or is_domain):
                        violations.append(f"{path}:{node.lineno} importa {mod_name}")
                        
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    continue  # Import relativo é interno e permitido
                
                if node.module:
                    mod_name = node.module
                    top_name = mod_name.split(".")[0]
                    
                    is_stdlib = top_name in sys.stdlib_module_names
                    is_domain = mod_name == "dispute_analyst.domain" or mod_name.startswith("dispute_analyst.domain.")
                    
                    if not (is_stdlib or is_domain):
                        violations.append(f"{path}:{node.lineno} importa {mod_name}")

    assert not violations, "\n".join(violations)
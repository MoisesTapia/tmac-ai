"""DOCS/RULES.md must match the rule YAML files (it is generated, not hand-written)."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate_rules_doc.py"


def test_rules_doc_is_up_to_date():
    spec = importlib.util.spec_from_file_location("generate_rules_doc", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (
        module.main(["--check"]) == 0
    ), "DOCS/RULES.md is stale; run: python scripts/generate_rules_doc.py"

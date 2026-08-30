"""Executable drift detection: the invariants this repository claims to hold.

These were previously a checklist a person had to run by hand. Each one
corresponds to a defect that actually shipped and survived for months, so they
are asserted rather than documented.
"""
import ast
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SRC_FILES = sorted(ROOT.joinpath("src").rglob("*.py"))
CODE_FILES = SRC_FILES + [ROOT / "benchmark.py"]

MEASURED_KEYS = {"objective_value", "cut_value", "standard_error",
                 "best_sampled_value", "runtime_seconds", "expectation_value"}


def _calls(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)]


def _is_numeric_default(node) -> bool:
    """A default only fabricates if it can be mistaken for a measurement.

    `.get('objective_value', 0.0)` is the archetype and is banned. `None` and
    a string like 'N/A' are honest sentinels -- a reader cannot mistake either
    for a computed value -- so they are allowed. The rule is about numbers, not
    about `.get`.
    """
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _is_numeric_default(node.operand)
    # float('-inf'), float(0), np.nan and friends.
    if isinstance(node, ast.Call):
        f = node.func
        name = getattr(f, "id", None) or getattr(f, "attr", None)
        return name in {"float", "int", "nan", "inf"}
    return False


@pytest.mark.parametrize("path", CODE_FILES, ids=lambda p: p.name)
def test_no_measured_quantity_is_read_with_a_numeric_default(path):
    """`quantum_result.get('objective_value', 0.0)` is the archetype.

    A numeric default turns "nothing computed this" into a value the caller
    cannot distinguish from a measurement -- the comparison scored a real MILP
    optimum against exactly that. Checked with the AST rather than grep, so
    docstrings describing the historical bug do not trip it.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for call in _calls(tree):
        func = call.func
        if not (isinstance(func, ast.Attribute) and func.attr == "get"):
            continue
        if len(call.args) < 2:
            continue
        key, default = call.args[0], call.args[1]
        if (isinstance(key, ast.Constant) and key.value in MEASURED_KEYS
                and _is_numeric_default(default)):
            pytest.fail(
                f"{path.relative_to(ROOT)}:{call.lineno} reads "
                f"{key.value!r} with the numeric default "
                f"{ast.unparse(default)}")


@pytest.mark.parametrize("path", SRC_FILES, ids=lambda p: p.name)
def test_every_source_module_imports(path):
    """A module nothing imports is a module nothing has ever checked."""
    rel = path.relative_to(ROOT).with_suffix("")
    if rel.name == "__init__":
        rel = rel.parent
    importlib.import_module(str(rel).replace("/", "."))


def test_every_source_module_is_reached_by_some_test():
    """The invariant that would have caught qaoa.py.

    It was the only real quantum solver here, had no test and no caller, and
    when finally run it decoded every measurement to all-zeros and reported a
    cut of 0.0 on a graph whose optimum is 4.
    """
    imported = set()
    for test in ROOT.joinpath("tests").glob("test_*.py"):
        tree = ast.parse(test.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)

    unreached = []
    for path in SRC_FILES:
        if path.name == "__init__.py":
            continue
        module = str(path.relative_to(ROOT).with_suffix("")).replace("/", ".")
        if not any(m == module or m.startswith(module + ".") for m in imported):
            unreached.append(module)
    assert not unreached, f"source modules no test imports: {unreached}"


def test_the_interpreter_bound_is_declared_where_pip_enforces_it():
    """mitiq cannot install on 3.12+, and prose in a README does not stop it."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.10,<3.12"' in pyproject


def test_there_is_only_one_dependency_manifest():
    """Two manifests that disagree was the largest set of unbacked claims here."""
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    declared = [ln for ln in requirements.splitlines()
                if ln.strip() and not ln.strip().startswith("#")]
    assert declared == ["-e .[test]"], declared

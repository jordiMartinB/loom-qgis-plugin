import os
import sys
import importlib
import pytest
import tempfile
import shutil
from pathlib import Path


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(TEST_DIR, "..", "..", ".."))


@pytest.fixture
def wrapper(monkeypatch, tmp_path):
    # Create mock backend module
    mock_backend_py = Path(TEST_DIR) / "backend_mock.py"
    mock_backend_py.write_text("""
def run_topo(args):
    return f"topo: {args[0][:20]}... + config"

def run_loom(args):
    return f"loom: {args[0][:20]}... + config"

def run_octi(args):
    return f"octi: {args[0][:20]}... + config"

def run_transitmap(args):
    return f"transitmap: {args[0][:20]}... + config"
""")

    # Set up sys.path
    wrapper_dir = str(Path(PROJ_ROOT) / "src" / "loom")
    monkeypatch.syspath_prepend(wrapper_dir)
    monkeypatch.syspath_prepend(TEST_DIR)

    # Point to mock backend
    monkeypatch.setenv("LOOM_BACKEND_MODULE", "backend_mock")

    # Clear module cache
    for mod in ("wrapper", "backend_mock", "loom"):
        sys.modules.pop(mod, None)

    wrapper = importlib.import_module("wrapper")

    yield wrapper

    # Cleanup
    for mod in ("wrapper", "backend_mock", "loom"):
        sys.modules.pop(mod, None)
    mock_backend_py.unlink(missing_ok=True)


def test_proxy_functions_with_correct_signatures(wrapper):
    """Test that wrapper functions accept (graph_json, config_json) and call backend."""
    graph = '{"nodes": [], "edges": []}'
    config = '{"max-aggr-dist": 50}'

    result = wrapper.run_topo(graph, config)
    assert "topo:" in result
    assert graph[:20] in result

    result = wrapper.run_loom(graph, config)
    assert "loom:" in result

    result = wrapper.run_octi(graph, config)
    assert "octi:" in result

    result = wrapper.run_transitmap(graph, config)
    assert "transitmap:" in result
import os
import shutil
import subprocess
import sys

import pytest
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def run_build(dest):
    """Build all four faces into `dest` and return {style: path}."""
    subprocess.run([sys.executable, "build.py"], cwd=ROOT, check=True)
    os.makedirs(dest, exist_ok=True)
    dist = os.path.join(ROOT, "dist")
    paths = {}
    for style in _build().STYLES:
        name = f"AstacidMono-{style}.ttf"
        out = os.path.join(dest, name)
        shutil.copy(os.path.join(dist, name), out)
        paths[style] = out
    return paths


def _build():
    import build

    return build


@pytest.fixture(scope="session")
def build_module():
    return _build()


@pytest.fixture(scope="session")
def dist(tmp_path_factory):
    """One build shared across the whole session (a build is ~2 min)."""
    return run_build(tmp_path_factory.mktemp("dist"))


@pytest.fixture(scope="session")
def fonts(dist):
    return {style: TTFont(path) for style, path in dist.items()}

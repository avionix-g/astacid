import hashlib

from conftest import run_build


def _digest(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_bit_for_bit_reproducible(dist, tmp_path):
    """A second independent build is byte-identical to the first."""
    second = run_build(tmp_path / "second")
    for style, first_path in dist.items():
        assert _digest(first_path) == _digest(second[style]), style

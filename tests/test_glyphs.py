import hashlib
import os

import pytest
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from ufoLib2 import Font as UFO

from build import STYLES


def glyph_hash(font, codepoint):
    """Stable digest of a glyph's outline, reached by codepoint."""
    glyf = font["glyf"]
    gname = font.getBestCmap()[codepoint]
    pen = RecordingPen()
    glyf[gname].draw(pen, glyf)
    return hashlib.sha256(repr(pen.value).encode()).hexdigest()


def test_changed_matches_override_sources(build_module):
    """render.CHANGED stays in sync with the actual override glyphs."""
    import render

    ufo = UFO.open(build_module.SOURCES / "overrides.ufo")
    cps = {g.unicode for g in ufo if g.unicode is not None}
    assert cps == set(render.CHANGED)


@pytest.mark.parametrize("style", STYLES)
def test_all_faces_present(dist, style):
    assert os.path.exists(dist[style])


@pytest.mark.parametrize("cp", [0x30, 0x24, 0x7E])  # zero, dollar, tilde
def test_override_replaces_stock_outline(fonts, build_module, cp):
    """Patched glyphs differ from stock DejaVu and keep the monospace cell width."""
    dejavu = TTFont(os.path.join(os.environ["DEJAVU_DIR"], "DejaVuSansMono.ttf"))
    astacid = fonts["Regular"]
    assert glyph_hash(astacid, cp) != glyph_hash(dejavu, cp)
    gname = astacid.getBestCmap()[cp]
    assert astacid["hmtx"][gname][0] == build_module.CELL


@pytest.mark.parametrize("style", STYLES)
def test_nerd_glyphs_added(fonts, style):
    # A representative Nerd Font codepoint (Powerline right arrow, U+E0B0).
    assert 0xE0B0 in fonts[style].getBestCmap()

import pytest
from fontTools.misc.timeTools import epoch_diff

from build import STYLES

# fsSelection / macStyle bit positions. Restated (not imported from build) on
# purpose: the test's job is to independently assert the expected bits, so a
# typo in build.py can't silently propagate into a passing test.
ITALIC, BOLD, REGULAR, USE_TYPO = 1 << 0, 1 << 5, 1 << 6, 1 << 7
MAC_BOLD, MAC_ITALIC = 1 << 0, 1 << 1


def name(font, nid):
    rec = font["name"].getName(nid, 3, 1, 0x409)
    return rec.toUnicode() if rec else None


@pytest.mark.parametrize("style", STYLES)
def test_timestamp_is_hardcoded_epoch(fonts, build_module, style):
    # Nix's stdenv exports SOURCE_DATE_EPOCH=315532800 during the build;
    # the embedded timestamp must still be our hardcoded EPOCH, not that.
    head = fonts[style]["head"]
    unix = head.created + epoch_diff
    assert unix == build_module.EPOCH
    assert head.created == head.modified


@pytest.mark.parametrize(
    "style,bold,italic",
    [
        ("Regular", False, False),
        ("Bold", True, False),
        ("Oblique", False, True),
        ("BoldOblique", True, True),
    ],
)
def test_style_bits(fonts, style, bold, italic):
    os2 = fonts[style]["OS/2"]
    head = fonts[style]["head"]
    assert bool(os2.fsSelection & BOLD) == bold
    assert bool(os2.fsSelection & ITALIC) == italic
    assert bool(os2.fsSelection & REGULAR) == (not bold and not italic)
    assert os2.fsSelection & USE_TYPO  # always set
    assert bool(head.macStyle & MAC_BOLD) == bold
    assert bool(head.macStyle & MAC_ITALIC) == italic


@pytest.mark.parametrize("style", STYLES)
def test_vendor_and_family(fonts, build_module, style):
    f = fonts[style]
    assert f["OS/2"].achVendID.strip() == build_module.VENDOR
    assert name(f, 1) == build_module.FAMILY  # RIBBI family
    assert name(f, 16) == build_module.FAMILY  # typographic family


def test_subfamily_uses_oblique_not_italic(fonts):
    # RIBBI subfamily (2) says Italic; typographic subfamily (17) says Oblique.
    assert name(fonts["Oblique"], 2) == "Italic"
    assert name(fonts["Oblique"], 17) == "Oblique"


@pytest.mark.parametrize("style", STYLES)
def test_font_revision(fonts, build_module, style):
    assert fonts[style]["head"].fontRevision == build_module.REVISION

#!/usr/bin/env fontforge
"""One-time synthesis of the Bold / Oblique / BoldOblique override layers from
the hand-drawn Book overrides (sources/overrides.sfd).

NOT part of the reproducible build. This derives starting points that then
become hand-edited source of truth (like extract-overrides.py). Re-run only to
regenerate from scratch before touch-ups; touch-ups are applied to the output
SFDs afterward and must not be clobbered by re-running this.

Rules (mirroring how DejaVu 2.37 itself relates its mono faces — measured):
  Oblique      : glyphs DejaVu keeps upright (% * ^ _ ~) are copied as-is;
                 the rest are skewed +11 deg about the baseline, then re-fit
                 centred in the 1233 cell.
  Bold         : changeWeight(+55) — DejaVu Bold thickens stems 172 -> 227.
  BoldOblique  : Bold then the Oblique rule.
"""
import fontforge, psMat, math

CELL = 1233
ANGLE = 11                       # DejaVu mono italic angle is -11 deg (lean right)
EMBOLDEN = 55                    # measured book->bold stem delta ('|': 172->227)
UPRIGHT = {0x25, 0x2A, 0x5E, 0x5F, 0x7E}   # % * ^ _ ~  (DejaVu leaves these upright)
SKEW = psMat.skew(math.radians(ANGLE))


def recenter(g):
    bb = g.boundingBox()
    target_lsb = round((CELL - (bb[2] - bb[0])) / 2.0)
    g.transform(psMat.translate(target_lsb - bb[0], 0))
    g.width = CELL


def embolden(g):
    g.changeWeight(EMBOLDEN, "auto", 0, 0, "auto")
    g.width = CELL


def obliquify(g):
    if g.unicode in UPRIGHT:
        g.width = CELL
        return
    g.transform(SKEW)
    recenter(g)


def build(out_name, family, fontname, ops):
    f = fontforge.open("sources/overrides.sfd")
    f.is_quadratic = False           # changeWeight needs cubic splines
    for g in f.glyphs():
        for op in ops:
            op(g)
        g.removeOverlap()
        g.simplify()
    f.is_quadratic = True            # back to TrueType outlines
    for g in f.glyphs():
        g.round()
        g.width = CELL
    f.familyname = family
    f.fontname = fontname
    f.fullname = family
    f.italicangle = -ANGLE if obliquify in ops else 0
    f.save("sources/%s" % out_name)
    print("wrote sources/%s" % out_name)


build("overrides-bold.sfd",        "Astacid Overrides Bold",         "AstacidOverridesBold",        [embolden])
build("overrides-oblique.sfd",     "Astacid Overrides Oblique",      "AstacidOverridesOblique",     [obliquify])
build("overrides-boldoblique.sfd", "Astacid Overrides BoldOblique",  "AstacidOverridesBoldOblique", [embolden, obliquify])

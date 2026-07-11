#!/usr/bin/env bash
# Reproducible Astacid Mono build: merge -> Nerd-patch -> metadata -> dist/.
# Assumes fontforge, nerd-font-patcher, python3+fonttools on PATH and
# $DEJAVU_DIR set (the flake devShell / package provides both).
set -euo pipefail
cd "$(dirname "$0")"

: "${DEJAVU_DIR:?set DEJAVU_DIR to the pristine DejaVu Sans Mono 2.37 dir}"
: "${SOURCE_DATE_EPOCH:=315532800}"; export SOURCE_DATE_EPOCH

RAW=build/raw; PATCHED=build/patched; DIST=dist
STYLES=(Regular Bold Oblique BoldOblique)

rm -rf build "$DIST"
mkdir -p "$RAW" "$PATCHED" "$DIST"

echo ">> stage 1: merge overrides onto base"
fontforge -lang=py -script build.py "$RAW"

echo ">> stage 2: patch Nerd Font glyphs (--complete --mono)"
for st in "${STYLES[@]}"; do
  tmp="$PATCHED/$st.d"; mkdir -p "$tmp"
  nerd-font-patcher --complete --mono --quiet --no-progressbars \
    --outputdir "$tmp" "$RAW/AstacidMono-$st.ttf"
  mv "$tmp"/*.ttf "$PATCHED/AstacidMono-$st.ttf"
  rmdir "$tmp"
done

echo ">> stage 3: authoritative metadata"
for st in "${STYLES[@]}"; do
  python3 build_meta.py "$PATCHED/AstacidMono-$st.ttf" "$DIST/AstacidMono-$st.ttf" "$st"
done

echo ">> done. dist/:"
ls -1 "$DIST"

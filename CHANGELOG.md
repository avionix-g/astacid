## v2.0

- Rename family `Astacid` -> `Astacid Mono`.
- Add `Bold`, `Oblique`, `Bold Oblique` families to match DejaVu.
- Repatch with latest NerdFont.
- Fix glyphs with inconsistent advance size.

This release completely overhauls the font creation pipeline. Instead of a manually edited whole-font .sfd, the altered glyphs have been extracted to .ufo sources. Each set of glyphs is patched onto a clean DejaVu Sans Mono base, then the result is patched with the complete NerdFont set. The build process is based on a Nix flake for full reproducibility.

## v1.0

Initial release.
{
  description = "Astacid Mono — a DejaVu-based programming font (reproducible dev + build env)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f (import nixpkgs { inherit system; }));
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.fontforge            # glyph editing + build.py scripting engine
            pkgs.nerd-font-patcher    # binary: `nerd-font-patcher` (bundles the Nerd Font glyph set)
            # fontbakery (QA) — TEMPORARILY OMITTED. Broken in this pinned nixpkgs rev
            # (0bb7ec54, 2026-07-08): py3.14 build pulls incompatible `fs`; py3.12 build
            # fails on `shaperglot` (missing pkg_resources). Not needed until Phase 4 —
            # revisit then (bump pin, add a second good-rev input, or run via `uvx fontbakery`).
            pkgs.woff2                # woff2_compress for optional web artifact
            (pkgs.python3.withPackages (ps: [
              ps.fonttools            # ttx, subsetting, name-table surgery
              ps.brotli               # WOFF2 support for fonttools
            ]))
          ];

          shellHook = ''
            echo "astacid dev shell:"
            echo "  fontforge         $(fontforge --version 2>&1 | grep -oiE 'fontforge [0-9]+' | head -1)"
            echo "  nerd-font-patcher $(nerd-font-patcher --version 2>/dev/null | head -1)"
            echo "  fonttools         $(python3 -c 'import fontTools; print(fontTools.version)')"
            echo "  (fontbakery omitted — broken in pinned rev; see flake.nix)"
            export SOURCE_DATE_EPOCH=315532800   # deterministic font timestamps (1980-01-01)
          '';
        };
      });

      # Phase 4: uncomment once build.sh + sources/overrides.sfd + vendored base exist.
      # packages = forAllSystems (pkgs: {
      #   default = pkgs.stdenv.mkDerivation {
      #     pname = "astacid-mono";
      #     version = "2.0.0";
      #     src = self;
      #     nativeBuildInputs = [ pkgs.fontforge pkgs.nerd-font-patcher
      #       (pkgs.python3.withPackages (ps: [ ps.fonttools ps.brotli ])) ];
      #     SOURCE_DATE_EPOCH = 315532800;
      #     buildPhase = "bash build.sh";
      #     installPhase = ''
      #       install -Dm644 dist/*.ttf -t $out/share/fonts/truetype
      #     '';
      #   };
      # });
    };
}

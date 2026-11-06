{
  description = "Sami Ansari's résumé as HTML and PDF";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      eachSystem = nixpkgs.lib.genAttrs systems;
      src = nixpkgs.lib.fileset.toSource {
        root = ./.;
        fileset = nixpkgs.lib.fileset.unions [
          ./build.py ./resume.json ./index.template.html ./index.html ./resume.pdf ./assets
        ];
      };
      build = system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in pkgs.runCommand "resume" {
          nativeBuildInputs = [ pkgs.python3 pkgs.chromium pkgs.poppler-utils ];
          FONTCONFIG_FILE = pkgs.makeFontsConf { fontDirectories = [ ]; };
        } ''
          cp -r ${src} source
          chmod -R u+w source
          cd source
          cp index.html committed.html
          export PYTHONDONTWRITEBYTECODE=1
          python build.py
          cmp index.html committed.html || { echo "index.html is stale: run python build.py"; exit 1; }
          export HOME=$TMPDIR
          chromium --headless --no-sandbox --no-pdf-header-footer --virtual-time-budget=10000 --print-to-pdf=check.pdf "file://$PWD/index.html"
          for pdf in check.pdf resume.pdf; do
            pdfinfo $pdf | grep -qx "Pages: *1" || { echo "$pdf is not one page"; exit 1; }
            pdfinfo $pdf | grep -q "Page size: *612 x 792 pts" || { echo "$pdf is not US Letter"; exit 1; }
          done
          mkdir -p $out
          cp index.html resume.pdf $out/
          cp -r assets $out/
        '';
    in {
      packages = eachSystem (system: { default = build system; });
      checks = eachSystem (system: { site = self.packages.${system}.default; });
    };
}

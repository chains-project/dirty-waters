{
  description = "Construct development shell from requirements.txt";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  inputs.pyproject-nix.url = "github:nix-community/pyproject.nix";

  outputs =
    { nixpkgs, pyproject-nix, ... }:
    let
      # Load/parse requirements.txt
      project = pyproject-nix.lib.project.loadRequirementsTxt { projectRoot = ./.; };

      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      python = pkgs.python312;

      pythonEnv =
        (
          # Render requirements.txt into a Python withPackages environment
          pkgs.python312.withPackages (project.renderers.withPackages { inherit python; })
        );

    in
    {
      devShells.x86_64-linux.default = pkgs.mkShell { packages = [ pythonEnv pkgs.maven ]; };
    };
}
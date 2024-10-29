# dirty-waters

Dirty-waters automatically finds software supply chain issues in software projects by analyzing the available metadata of all dependencies, transitively.

Reference: [Dirty-Waters: Detecting Software Supply Chain Smells](http://arxiv.org/pdf/2410.16049), Technical report 2410.16049, arXiv, 2024.

By using dirty-waters, you identify the shady areas of your supply chain, which would be natural target for attackers to exploit.

Kinds of problems identified by dirty-waters

* Dependencies with no link to source code repositories (high severity)
* Dependencies with no tag / commit sha for release, impossible to have reproducible builds (high severity)
* Deprecated Dependencies (medium severity)
* Depends on a fork (medium severity)
* Dependencies with no build attestation (low severity)

Additionally, dirty-waters gives a supplier view on the dependency trees (who owns the different dependencies?)

dirty-waters is developed as part of the [Chains research project](https://chains.proj.kth.se/).

## NPM Support

### Installation
To set up the Dirty-Waters, follow these steps:

1. Clone the repository:
```
git clone https://github.com/chains-project/dirty-waters.git
cd dirty-waters
```

2. Set up a virtual environment and install dependencies:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd tool
```

In alternative, you may also use the Nix flake present in this repository.

3. Set up the GitHub API token (ideally, in a `.env` file):
```
export GITHUB_API_TOKEN=<your_token>
```

### Usage

Run the tool using the following command structure:
```
python main.py -p <project_repo_name> -v <release_version_old> -s -pm <package_manager> [-vn <release_version_new>] [-d]
```


#### Arguments:
```
usage: main.py [-h] -p PROJECT_REPO_NAME -v RELEASE_VERSION_OLD [-vn RELEASE_VERSION_NEW] -s [-d] -pm
               {yarn-classic,yarn-berry,pnpm} [--pnpm-scope]

options:
  -p PROJECT_REPO_NAME, --project-repo-name PROJECT_REPO_NAME
                        Specify the project repository name. Example: MetaMask/metamask-extension
  -v RELEASE_VERSION_OLD, --release-version-old RELEASE_VERSION_OLD
                        The old release tag of the project repository. Example: v10.0.0
  -vn RELEASE_VERSION_NEW, --release-version-new RELEASE_VERSION_NEW
                        The new release version of the project repository.
  -s, --static-analysis
                        Run static analysis and generate a markdown report of the project
  -d, --differential-analysis
                        Run differential analysis and generate a markdown report of the project
  -pm {yarn-classic,yarn-berry,pnpm,npm}, --package-manager {yarn-classic,yarn-berry,pnpm,npm}
                        The package manager used in the project.
  --pnpm-scope          Extract dependencies from pnpm with a specific scope
                        using 'pnpm list --filter <scope> --depth Infinity'
                        command. Configure the scope in tool_config.py file.
```


#### Example usage:
1. Software supply chain smell analysis:
```
python3 main.py -p MetaMask/metamask-extension -v v11.11.0 -s -pm yarn-berry
```

- Example output: [Software Supply Chain Smells Report Example](https://github.com/chains-project/dirty-waters/blob/main/example_reports/software_supply_chain_smells_report_example.md)

2. Differential analysis:
```
python3 main.py -p MetaMask/metamask-extension -v v11.11.0 -vn v11.12.0 -s -d -pm yarn-berry
```

Notes:
- `-v` should be the version of GitHub release, e.g. for [this release](https://github.com/MetaMask/metamask-extension/releases/tag/v11.1.0), the value should be `v11.11.0`, not `Version 11.11.0` or `11.11.0`.
- The `-s` flag is required for all analyses.
- When using `-d` for differential analysis, both `-v` and `-vn` must be specified.




## Java Support

### Installation

### Usage

Usage:
Example reports: TODO add link

## Academic Work
- [Dirty-Waters: Detecting Software Supply Chain Smells](https://arxiv.org/abs/2410.16049)


## Other issues not handled by dirty-waters

* Missing dependencies: simply run mvn/pip/... install :)
* Bloated dependencies: we recommend [DepClean](https://github.com/ASSERT-KTH/depclean) for Java, [depcheck](https://github.com/depcheck/depcheck) for NPM
* Version constraint inconsistencies: we recommend [pipdeptree](https://github.com/tox-dev/pipdeptree) for Python

## License

MIT License.

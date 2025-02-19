# dirty-waters

Dirty-waters automatically finds software supply chain issues in software projects by analyzing the available metadata of all dependencies, transitively.

Reference: [Dirty-Waters: Detecting Software Supply Chain Smells](http://arxiv.org/pdf/2410.16049), Technical report 2410.16049, arXiv, 2024.

By using `dirty-waters`, you identify the shady areas of your supply chain, which would be natural target for attackers to exploit.

`dirty-waters`'s static analyses report the following smells:

- Dependencies with no/invalid link to source code repositories (high severity)
- Dependencies with no tag/commit SHA for release, impossible to have reproducible builds (medium severity)
- Deprecated Dependencies (medium severity)
- Depends on a fork (medium severity)
- Dependencies without/with invalid code signature (medium severity)
- Dependencies with no build attestation (low severity)

As for its differential analyses, `dirty-waters` reports the following smells:

- Dependencies with code signature changes (high severity)
- Downgraded dependencies (medium severity)
- Dependencies with commits made by both new authors and reviewers (medium severity)
- Dependencies with commits approved by new reviewers (medium severity)
- Dependencies with new contributors (low severity)

Additionally, `dirty-waters` gives a supplier view on the dependency trees (who owns the different dependencies?)

`dirty-waters` is developed as part of the [Chains research project](https://chains.proj.kth.se/).

## Installation

### Installation via pip

You can install `dirty-waters` via pip:

```bash
pip install dirty-waters
# or
pipx install dirty-waters
```

Set up the GitHub API token (or with a `.env` file):

```bash
export GITHUB_API_TOKEN=<your_token>
```

## Usage

### Command line

Run the tool using the following command structure:

```
# analyzing the software supply chain of Maven project INRIA/spoon
$ dirty-waters -p INRIA/spoon -pm maven
```

All configuration options
```
usage: main.py [-h] -p PROJECT_REPO_NAME [-v RELEASE_VERSION_OLD]
               [-vn RELEASE_VERSION_NEW] [-d] [-n] -pm
               {yarn-classic,yarn-berry,pnpm,npm,maven}
               [--pnpm-scope PNPM_SCOPE] [--debug] [--no-gradual-report]
               [--check-source-code] [--check-release-tags]
               [--check-deprecated] [--check-forks] [--check-provenance]
               [--check-code-signature]

options:
  -h, --help            show this help message and exit
  -p PROJECT_REPO_NAME, --project-repo-name PROJECT_REPO_NAME
                        Specify the project repository name. Example:
                        MetaMask/metamask-extension
  -v RELEASE_VERSION_OLD, --release-version-old RELEASE_VERSION_OLD
                        The old release tag of the project repository.
                        Defaults to HEAD. Example: v10.0.0
  -vn RELEASE_VERSION_NEW, --release-version-new RELEASE_VERSION_NEW
                        The new release version of the project repository.
  -d, --differential-analysis
                        Run differential analysis and generate a markdown
                        report of the project
  -n, --name-match      Compare the package names with the name in the in the
                        package.json file. This option will slow down the
                        execution time due to the API rate limit of code
                        search.
  -pm {yarn-classic,yarn-berry,pnpm,npm,maven}, --package-manager {yarn-classic,yarn-berry,pnpm,npm,maven}
                        The package manager used in the project.
  --pnpm-scope PNPM_SCOPE
                        Extract dependencies from pnpm with a specific scope
                        using 'pnpm list --filter <scope> --depth Infinity'
                        command. Configure the scope in tool_config.py file.
  --debug               Enable debug mode.
  --no-gradual-report   Disable gradual report generation -- instead of one
                        smell type per report, gradually descending by
                        severity, report all.

smell checks:
  --check-source-code   Check for dependencies with no link to source code
                        repositories
  --check-release-tags  Check for dependencies with no tag/commit sha for
                        release
  --check-deprecated    Check for deprecated dependencies
  --check-forks         Check for dependencies that are forks
  --check-provenance    Check for dependencies with no build attestation
  --check-code-signature
                        Check for dependencies with missing/invalid code
                        signature
```

Reports are gradual by default: that is, only the highest severity smell type with issues found within this project is reported. You can disable this feature, and get a full report, by setting the `--no-gradual-report` flag to `true`. Note that if you ask for specific checks to be performed, the gradual report feature will also be disabled.

1. Static analysis:

```bash
# If manually cloned
python3 main.py -p MetaMask/metamask-extension -pm yarn-berry
# If installed via pip
dirty-waters -p MetaMask/metamask-extension -pm yarn-berry
```

- Example output: [Static Analysis Report Example](example_reports/static_analysis_report_example.md)

2. Differential analysis:

```bash
# If manually cloned
python3 main.py -p MetaMask/metamask-extension -v v11.11.0 -vn v11.12.0 -d -pm yarn-berry
# If installed via pip
dirty-waters -p MetaMask/metamask-extension -v v11.11.0 -vn v11.12.0 -d -pm yarn-berry
```

- Example output: [Differential Analysis Report Example](example_reports/differential_analysis_report_example.md)

Notes:

- `-v` should be the version of GitHub release, e.g. for [this release](https://github.com/MetaMask/metamask-extension/releases/tag/v11.1.0), the value should be `v11.11.0`, not `Version 11.11.0` or `11.11.0`.
- When using `-d` for differential analysis, `-vn` must be specified.

### Development

To set up `dirty-waters`, follow these steps:

1. Clone the repository:

```bash
git clone https://github.com/chains-project/dirty-waters.git
cd dirty-waters
```

2. Set up a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd tool
```

In alternative to virtual environments, you may also use the Nix flake present in this repository.

3. Set up the GitHub API token (ideally, in a `.env` file):

```bash
export GITHUB_API_TOKEN=<your_token>
```


### Continuous integration

See Github action at <https://github.com/chains-project/dirty-waters-action>

## Software Supply Chain Smell Support

`dirty-waters` currently supports package managers within the JavaScript and Java ecosystems. However, due to some constraints associated with the nature of the package managers, the tool may not be able to detect all the smells in the project. The following table shows the supported package managers and their associated smells, for static analysis:

| Package Manager | No Source Code Repository | Invalid Source Code Repository URL | No Release Tag | Deprecated Dependency | Depends on a Fork | No Build Attestation | No/Invalid Code Signature |
| --------------- | ------------------------- | ---------------------------------- | -------------- | --------------------- | ----------------- | -------------------- | ------------------------- |
| Yarn Classic    | Yes                       | Yes                                | Yes            | Yes                   | Yes               | Yes                  | Yes                       |
| Yarn Berry      | Yes                       | Yes                                | Yes            | Yes                   | Yes               | Yes                  | Yes                       |
| Pnpm            | Yes                       | Yes                                | Yes            | Yes                   | Yes               | Yes                  | Yes                       |
| Npm             | Yes                       | Yes                                | Yes            | Yes                   | Yes               | Yes                  | Yes                       |
| Maven           | Yes                       | Yes                                | Yes            | No                    | Yes               | No                   | Yes                       |

All package managers support every smell in the differential analysis scenario.

### Smell Check Options

By default, all supported checks for the given package manager are performed in static analysis.
You can specify individual checks using the following flags (note that if at least one flag
is passed, instead of all checks being performed, only the flagged ones will be):

- `--check-source-code`: Check for dependencies with no link to source code repositories
- `--check-release-tags`: Check for dependencies with no tag/commit sha for release
- `--check-deprecated`: Check for deprecated dependencies
- `--check-forks`: Check for dependencies that are forks
- `--check-provenance`: Check for dependencies with no build attestation
- `--check-code-signature`: Check for dependencies with no/invalid code signature

**Note**: The `--check-release-tags` and `--check-forks` flags require `--check-source-code` to be enabled, as release tags can only be checked if we can first verify the source code repository.

As an example of running specific checks:

```bash
dirty-waters -p MetaMask/metamask-extension -v v11.11.0 -pm yarn-berry --check-source-code --check-release-tags
```

This run will only check for dependencies with no link to source code repositories and dependencies with no tag/commit sha for release.

For **differential analysis**, it is currently not possible to specify individual checks -- all checks will be performed.

### Notes

#### Inaccessible Tags

Sometimes, the release version specified in a lockfile/pom/similar is not necessarily the same
as the tag used in the repository. This can happen for a variety of reasons. We have
compiled several tag formats which were deemed reasonable to lookup, if the exact tag
specified in the lockfile/pom/similar is not found. They come from a combination of [AROMA](https://dl.acm.org/doi/pdf/10.1145/3643764)'s
work and our own research on this subject.
These formats are the following:

<details> <summary>Tag formats</summary>

- `<tag>`
- `v<tag>`
- `r-<tag>`
- `release-<tag>`
- `parent-<tag>`
- `<package_name>@<tag>`
- `<package_name>-v<tag>`
- `<package_name>_v<tag>`
- `<package_name>-<tag>`
- `<package_name>_<tag>`
- `<repo_name>@<tag>`
- `<repo_name>-v<tag>`
- `<repo_name>_v<tag>`
- `<repo_name>-<tag>`
- `<repo_name>_<tag>`
- `<project_name>@<tag>`
- `<project_name>-v<tag>`
- `<project_name>_v<tag>`
- `<project_name>-<tag>`
- `<project_name>_<tag>`
- `release/<tag>`
- `<tag>-release`
- `v.<tag>`
- `p1-p2-p3<tag>`

As examples of what `package_name`, `repo_name`, and `project_name` could be, `maven-surefire`
is an interesting dependency:

- `maven-surefire-common` is the package name
- `maven-surefire` is the repo name (we remove the owner prefix)
- `surefire` is the project name

In particular, there are many `maven-*` dependencies whose tags follow these last conventions.

</details>

Note than this does not mean that if `dirty-waters` does not find a tag, it doesn't exist:
it means that it either doesn't exist, or that its format is not one of the above.

This list may be expanded in the future. If you feel that a relevant format is missing, please
open an issue and/or a pull request!

## Academic Work

- [Dirty-Waters: Detecting Software Supply Chain Smells](https://arxiv.org/abs/2410.16049)

## Other issues not handled by dirty-waters

- Missing dependencies: simply run mvn/pip/... install :)
- Bloated dependencies: we recommend [DepClean](https://github.com/ASSERT-KTH/depclean) for Java, [depcheck](https://github.com/depcheck/depcheck) for NPM
- Version constraint inconsistencies: we recommend [pipdeptree](https://github.com/tox-dev/pipdeptree) for Python

## License

MIT License.

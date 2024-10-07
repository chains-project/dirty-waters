# dirty-waters

Dirty-waters automatically finds software supply chain issues in software projects by analyzing the available metadata of all dependencies, transitively.

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

```
git clone https://github.com/chains-project/dirty-waters.git
cd dirty-waters
pip install -r requirements.txt
```

### Usage
Run the tool using the following command structure:
```
python main.py -w <wallet_repo_name> -v <release_version_old> -s -pm <package_manager> [-vn <release_version_new>] [-d]
```


#### Required Arguments:
```
- `-w, --wallet-repo-name`: Name of the wallet repository
- `-v, --release-version-old`: The release tag of the wallet repository to analyze.
- `-s, --static-analysis`: Run one version analysis and generate a markdown report of the project.
- `-pm, --package-manager`: Specify package manager (yarn-classic, yarn-berry, pnpm)
```

#### Optional Arguments:
```
- `-vn, --release-version-new`: Newer release version for comparison
- `-d, --differential-analysis`: Run differential analysis and generate a markdown report comparing two versions.
```


#### Example usage:
1. One version analysis:
```
python3 main.py -w metamask/metamask-extension -v 1.11.0 -s -pm yarn-berry
```

2. Differential analysis:
```
python3 main.py -w metamask/metamask-extension -v 1.11.0 -vn 1.12.0 -s -d -pm yarn-berry
```

Notes:
- The `-s` flag is required for all analyses.
- When using `-d` for differential analysis, both `-v` and `-vn` must be specified.

Example reports:
- [One version analysis]()
- [Differential analysis]()



## Java Support

### Installation

### Usage

Usage:
Example reports: TODO add link


## Other issues not handled by dirty-waters

* Missing dependencies: simply run mvn/pip/... install :)
* Bloated dependencies: we recommend [DepClean](https://github.com/ASSERT-KTH/depclean) for Java, [depcheck](https://github.com/depcheck/depcheck) for NPM
* Version constraint inconsistencies: we recommend [pipdeptree](https://github.com/tox-dev/pipdeptree) for Python

## License

MIT License.

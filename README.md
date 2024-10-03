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

TODO

### Usage

To be documented

Example reports: TODO add link

## Java Support

### Installation

### Usage

Usage:
Example reports: TODO add link


## Other issues not handled by dirty-waters

* Bloated dependencies: we recommend [DepClean](https://github.com/ASSERT-KTH/depclean) for Java, [depcheck](https://github.com/depcheck/depcheck) for NPM


## License

MIT License.

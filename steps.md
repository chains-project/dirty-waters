latest update: 01/20/2024

## Get all depencies list
To get all the dependencies used in [MetaMask Extension 11.4.1](https://github.com/MetaMask/metamask-extension/releases/tag/v11.4.1), firstly we use command `yarn list` to get the dependency tree and saved it to [11.4.1_extension_tree.txt](wallets/Metamask/deps_list/11.4.1_extension_tree.txt). Then [extract script](/wallets/Metamask/deps_list/extract_deps.py) is used to get the list of all dependencies:
- *_deps_list_gav.txt contains all dependencies including patches and version
- *_without_npm_nopatchdetail.txt contains all dependencies including version and patch's dependency but exclude patches details and 'npm' string(so the patch here doesn't have version)
- *_deps_list_nopatchdetail.txt excude all version info

we use *_withouxt_npm_nopatchdetail.txt for future analysis

for Metamask 11.4.1, `deps_list_gav.txt` contains 3335 dependencies. `without_npm_nopatchdetail` contains 3329 dependencies, that's because some of the patches are made for the same dependency. `deps_list_nopatchdetail` contains 2628 dependencies since some dependencies have different resolutions.

## Get repo info
We get 3301 github repository by running [get_github_repo](wallets/Metamask/deps_github_output/get_github_repo.py) with [*_without_npm_nopatchdetail](wallets/Metamask/deps_list/11.4.1_extension_tree_deps_list_gav_without_npm_nopatchdetail.txt) among which 26 depencies didn't find repo and 2 are hosted on gitea. 
We [manually insepected](wallets/Metamask/deps_github_output/manual_inspect_undefined.md) the 26 depencies, -> 7 reasons

## Track lines and authors
run in local enviroment: [here](new_release_change.py)

## deps publish data info(old)
[here](wallets/Metamask/deps_publish_date_old)

## github repo stastics(old)
[here](wallets/Metamask/repo_stastics_old)

---

### Steps(Old):

## Deps Info
1. get dependency tree:

`yarn list` or `yarn info -R`

2. get the dependency list: 

`extract_deps.py` - get list from tree 

> all deps(with different version):3335

> unique deps: 2643

3. Publish date & Last modified date
`npm view "$package" time --json`


4. get publish time of specific version: specificTime_sorted.json

### Repo info
1. get repos of packages `get_repo.py`:

`yarn info {packages} repository.url`

> repo on github: 3261

> undefined repo of packages: 26

> 2 link on gittea?

> 46 patches

> ⬆️ sum: 3335 -> checkout [line 11](https://github.com/chains-project/crypto_wallets/blob/main/steps.md#L11)

> unique repo: 2062

`github_repos_unique.txt`

2. get total number of contributors and commits of unique repo [line 35](https://github.com/chains-project/crypto_wallets/blob/main/steps.md#L35)

repo stats: `repository_stats.json`

> 1984 repositories 

> 78 errors

3. Get summary of repos

summary: `repository_stats_report_contributor_count.md`

Q? why unique deps' repos are different from deps' unique repo




Memo

total keys `jq 'keys | length' filename.json`

total value `jq '[..|scalars] | length' filename.json`

https://git-scm.com/docs/git-diff

`git log --numstat --format=%aN`

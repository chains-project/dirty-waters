Steps:

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


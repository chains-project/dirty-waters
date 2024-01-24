latest update: 01/20/2024

## Get all dependencies list
To get all the dependencies used in [MetaMask Extension 11.4.1](https://github.com/MetaMask/metamask-extension/releases/tag/v11.4.1), firstly we use command `yarn list` to get the dependency tree and saved it to [11.4.1_extension_tree.txt](wallets/Metamask/deps_list/11.4.1_extension_tree.txt). Then [extract script](/wallets/Metamask/deps_list/extract_deps.py) is used to get the list of all dependencies:
- *_deps_list_gav.txt contains all dependencies including patches and version
- *_without_npm_nopatchdetail.txt contains all dependencies including version and patch's dependency but exclude patches details and 'npm' string(so the patch here doesn't have version)
- *_deps_list_nopatchdetail.txt excude all version info

we use *_withouxt_npm_nopatchdetail.txt for future analysis

for Metamask 11.4.1, `deps_list_gav.txt` contains 3335 dependencies. `without_npm_nopatchdetail` contains 3329 dependencies, that's because some of the patches are made for the same dependency. `deps_list_nopatchdetail` contains 2628 dependencies since some dependencies have different resolutions.

### why we get some `@patch` in the dependencies?

we run `find_patch_count.sh` with  `deps_list_gav.txt` to get the [patch list](wallets/Metamask/deps_list/patch_list.txt), the result shows there are 46 patches in the dependency list.
we manually [insepect](wallets/Metamask/deps_list/manual_inspect_patches_11.4.1.md) the patch list by comparing them with the 44 patch files in `./yarn/patches` . 6 patch files are in `.yarn/patches` but couldn't find in dep list, which may indicates they were not used. and 8 are in dep list but couldn't be found in ./yarn/patches, all of them are optional.

#### Where does the file name come from?
run `yarn patch` and edit in a folder then run `yarn patch-commit -s`, Yarn will store a patchfile based on your changes.
The patch file(and patch file name) will be generated automatically
The `package.json` file will be updated automatically

e.g. "@0xsequence/abi@^0.36.13": "patch:@0xsequence/abi@npm%3A0.36.13#./.yarn/patches/@0xsequence-abi-npm-0.36.13-79fdcc587d.patch"

```
yarn patch @0xsequence/abi@npm:0.36.13 
➤ YN0000: Package @0xsequence/abi@npm:0.36.13 got extracted with success!
➤ YN0000: You can now edit the following folder: /private/var/folders/5b/0wll72f11md4mz224__zlv_80000gn/T/xfs-33a12158/user
➤ YN0000: Once you are done run yarn patch-commit -s /private/var/folders/5b/0wll72f11md4mz224__zlv_80000gn/T/xfs-33a12158/user and Yarn will store a patchfile based on your changes.
➤ YN0000: Done in 1s 537ms
```
Ref:
- https://yarnpkg.com/features/patching
- https://itnext.io/patch-an-npm-dependency-with-yarn-ddde2e194576

*filename example*:
- package name: @babel/runtime@patch
- for which version: @babel/runtime@npm%3A7.23.2
- patch path: #~/.yarn/patches/@babel-runtime-npm-7.23.2-d013d6cf7e.patch
- metadata(for integrity): ::version=7.23.2&hash=7df10d 

### Who add the patches and why?
developers make small changes to a dependency
who: `git log --pretty=format:'%an <%ae>' -- .yarn/patches  | sort | uniq -c | sort -nr`


## Get repo info
We get 3301 github repository by running [get_github_repo](wallets/Metamask/deps_github_output/get_github_repo.py) with [*_without_npm_nopatchdetail](wallets/Metamask/deps_list/11.4.1_extension_tree_deps_list_gav_without_npm_nopatchdetail.txt) among which 26 depencies didn't find repo and 2 are hosted on gitea. 
We [manually insepected](wallets/Metamask/deps_github_output/manual_inspect_undefined.md) the 26 depencies, -> 7 reasons


Who contributed to `yarn.lock` the most:
`git log --format='%an%ae' yarn.lock | sort | uniq -c | sort -nr`
162 Mark Stacey markjstacey@gmail.com
112 Whymarrh Whitby whymarrh.whitby@gmail.com
77 Erik Marks 25517051+rekmarks@users.noreply.github.com

`package.json`
309 kumavis aaron@kumavis.me
240 Mark Stacey markjstacey@gmail.com
197 Dan Finlay dan@danfinlay.com


## Track lines and authors
run in local enviroment: [here](trace/new_release_change.py)

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


Yarn v2 

**dep**

`yarn info -R`

https://yarnpkg.com/cli/info

Yarn v1
**warning & error**

`yarn check > xx.txt 2>&1` 

**dep**

https://classic.yarnpkg.com/en/docs/cli/list

`yarn list`

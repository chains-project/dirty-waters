latest update: 03/20/2024

**Table of Contents**
- [Steps](#steps)
  - [Tool Logic](#tool-logic)
  - [Download source code](#download-source-code)
  - [Get all dependencies list](#get-all-dependencies-list)
  - [Get repo info](#get-repo-info)
  - [Deps Info](#deps-info)
  - [The tool](#the-tool)
- [memo](#memo)
- [details](#details)
  
Tool:
functionA(for one relese): 
- npm deprecate, latest update time, provenance
- github available/archived/redirected/name_match/latest update time/open PR/(Scorecard)
- 

functionB(Compare two release):
- new controbutor
- new reviewer 
- new merger

- npm deprecate status
- archive status(archivedAt vs updatedAt)
- contributor access 

- who release the tag

- CI

Minutes 03/20/24
how to present the findings?:
1. deprecatd, packages without source code 
2. unarchived deprecated repo

3. newly added packages and packages with old version
4. for commits? 
- one commit used by many release
- are the author new?

- We write sperate results for each wallet in chapter4 and discuss the result in Discussion part.

for report:
- Good numbers
- Bad numbers / Warning
We remove All Versions Deprecated Packages

We keep :
- specific version deprecated packages
- Total packages
- GitHub URL does not exist
- Forks 

Other info>
We keep:
- Source code repo is not GitHub
- Names do not match

Output:
The list of all packages will be provided in a different markdown

Differenciating mode:
- We keep info about downgrading updates
- Repo metric to catch an attack from a package supplier
- Add a warning section if a new author has a spread commit




renovate
NOW
- coding tool: 
- argPaser
- database
- report
- Writing chapter4: tool

TODO


Minutes 03/13/24
NOW
- coding tool
TODO
- ✅ process patch
- process yarn.lock v1 file
- metamask-crx@workspace:.


Minutes 03/06/24

Progress:
1. ✅ identify new author to commit
2. ✅ identify new reviewer to review


Q:
1. archived status: No log 
2. Maintainer: need permission [link](https://github.com/chains-project/crypto_wallets/blob/main/differential/collaborator.graphql) [codeowner](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners): Code owners are automatically requested for review when someone opens a pull request that modifies code that they own.

3. PR merger: no endpoint -> need to go through all prs of a author or a repo
https://docs.github.com/en/graphql/reference/objects#pullrequest
4. Evaluation
three latest version

Todo:
ownerChange -> handle change
We may intergrated scorecard
Metrics






Minutes 02/28/34
indictor
- and what is missing so far
- metrics -score change

**To be solved**
1. Code search in fork 
2. Time issue
3. Make them automated
4. Consistency of the use of yarn and npm
5. Check Socket.dev

Minutes 02/26/34
Q:
1. For evaluation, do we want all versions' experiments and what should we include
- comparing 
- project

Working on tooling and chapter 3 writing
- to consider evaluation
optionA: look at major releases from three wallets
OptionB: look at latest ten releases from three wallets
OptionC: ablation study before and after an attack, maybe the one from 2023




Minutes 02/21/2024
Q
1. Github doesn't have record about owner transfer



Minutes 02/19/2024
Q:
1. Does execution time matter?
2. Evaluation what info do we want
- owner change
- new contributor
- (who review&merge)
- (CI) - how many CI skipped?
- if the github didn't updated but npm is updating
3. : contributor? owner change?
4. (fork)
5. how automated it should be

DO they change the owner?
mathjs-min
compare repo changes

Others:
besides, doesn't mean the source code is the same as packages in npm
discrepancy


# Tool Logic
Statistical analysis
- dep_list -> repo_list -> get pkg and repo info
Differential analysis
- two_dep_list -> two_repo_list -> 
  - compare commits



# Steps

## Download source code
`yarn install`

## Get all dependencies list
To get all the dependencies used in [MetaMask Extension 11.4.1](https://github.com/MetaMask/metamask-extension/releases/tag/v11.4.1), firstly we use command `yarn list`(`yarn info --recursive`) to get the dependency tree and saved it to [11.4.1_extension_tree.txt](wallets/Metamask/deps_list/11.4.1_extension_tree.txt). Then [extract script](/wallets/Metamask/deps_list/extract_deps_latest.py) is used to get the list of all dependencies:
- *_deps_list_gav.txt contains all dependencies including patches and version
- *_gav_without_npm.txt contains all dependencies including version but exclude all patches
- *_deps_list.txt excude all version info(also without all patches)
- *_deps_list_patches.txt contains all the patches

we use *_withouxt_npm.txt for future analysis

for Metamask 11.4.1, `deps_list_gav.txt` contains 3335 dependencies. `without_npm` contains 3289 dependencies, that's because the 46 patches are excluded . `deps_lis` contains 2603 dependencies since some dependencies have different resolutions.`deps_list_patches` contains 46 patches.



## Get repo info
We get 3301 github repository by running [get_github_repo](wallets/Metamask/deps_github_output/get_github_repo.py) with [*_without_npm_n](wallets/Metamask/deps_list/11.4.1_extension_tree_deps_list_gav_without_npm.txt) among which 26 dependencies didn't find repo and 2 are hosted on gitea. 
We [manually insepected](wallets/Metamask/deps_github_output/manual_inspect_undefined.md) the 26 depencies, -> 7 reasons

<details open>
  <summary>Who contributed to `yarn.lock` the most:</summary>

Who contributed to `yarn.lock` the most:

`git log --format='%an%ae' yarn.lock | sort | uniq -c | sort -nr`
- 162 Mark Stacey markjstacey@gmail.com
- 112 Whymarrh Whitby whymarrh.whitby@gmail.com
- 77 Erik Marks 25517051+rekmarks@users.noreply.github.com

`package.json`

- 309 kumavis aaron@kumavis.me
- 240 Mark Stacey markjstacey@gmail.com
- 197 Dan Finlay dan@danfinlay.com
</details>



## How do we know if the registry repo is the true repo?
Thinking:
-if the first version is validated? -> no
- if github have the registry info? -> no

besides, doesn't mean the source code is the same as packages in npm
discrepancy

## Track lines and authors
run in local enviroment: [here](trace/new_release_change.py)

In ideal situation(or as best practice), the each npm version should be sync with the github repository commit(release(tag) or package)



## The tool

| package name with resolution | package deprecated? | repo exist? | repo archived? | name match? |
|---------------|--------------|-------------|----------------|-------------|
| 1                            | 2                   | 3           | 4              | 5           |





## deps publish data info(old)
[here](wallets/Metamask/deps_publish_date_old)

## github repo stastics(old)
[here](wallets/Metamask/repo_stastics_old)

---

### Steps(Old):

## Get all dependencies list
To get all the dependencies used in [MetaMask Extension 11.4.1](https://github.com/MetaMask/metamask-extension/releases/tag/v11.4.1), firstly we use command `yarn list` to get the dependency tree and saved it to [11.4.1_extension_tree.txt](wallets/Metamask/deps_list/11.4.1_extension_tree.txt). Then [extract script](/wallets/Metamask/deps_list/extract_deps.py) is used to get the list of all dependencies:
- *_deps_list_gav.txt contains all dependencies including patches and version
- *_without_npm_nopatchdetail.txt contains all dependencies including version and patch's dependency but exclude patches details and 'npm' string(so the patch here doesn't have version)
- *_deps_list_nopatchdetail.txt excude all version info
- *_deps_list_patches.txt contains all the patches

we use *_withouxt_npm_nopatchdetail.txt for future analysis

for Metamask 11.4.1, `deps_list_gav.txt` contains 3335 dependencies. `without_npm_nopatchdetail` contains 3329 dependencies, that's because some of the patches are made for the same dependency. `deps_list_nopatchdetail` contains 2628 dependencies since some dependencies have different resolutions.`deps_list_patches` contains 46 patches.

## Get repo info
We get 3301 github repository by running [get_github_repo](wallets/Metamask/deps_github_output/get_github_repo.py) with [*_without_npm_nopatchdetail](wallets/Metamask/deps_list/11.4.1_extension_tree_deps_list_gav_without_npm_nopatchdetail.txt) among which 26 dependencies didn't find repo and 2 are hosted on gitea. 
We [manually insepected](wallets/Metamask/deps_github_output/manual_inspect_undefined.md) the 26 depencies, -> 7 reasons

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


## Details
<details open>
  <summary>Details</summary>

  ### why we get some `@patch` in the dependencies?

 we run `find_patch_count.sh` with  `deps_list_gav.txt` to get the [patch list](wallets/Metamask/deps_list/patch_list.txt), the result shows there are 46 patches in the dependency list.
 we manually [insepect](wallets/Metamask/deps_list/manual_inspect_patches_11.4.1.md) the patch list by comparing them with the 44 patch files in `./yarn/patches` . 6 patch files are in `.yarn/patches` but couldn't find in dep list, which may indicates they were not used. and 8 are in dep list but couldn't be found in ./yarn/patches, all of them are optional.

- (works for v2 and above)run `yarn patch` and edit in a folder then run `yarn patch-commit -s`, Yarn will store a patchfile based on your changes.
- The patch file(and patch file name) will be generated automatically
- The `package.json` file will be updated automatically
Basically, the software use these dependencies, but the resolution is with patches.
e.g. in `package.json`: "@0xsequence/abi@^0.36.13": "patch:@0xsequence/abi@npm%3A0.36.13#./.yarn/patches/@0xsequence-abi-npm-0.36.13-79fdcc587d.patch"

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


### Actual situation
#### not sync with github repo
##### at all
- https://github.com/apocentre/sampling
- https://www.npmjs.com/package/@apocentre/alias-sampling 

##### some are synced, some are not

- https://github.com/apollographql/subscriptions-transport-ws
- https://www.npmjs.com/package/@httptoolkit/subscriptions-transport-ws/v/0.11.2?activeTab=versions
- https://github.com/trufflesuite/bigint-buffer
- https://www.npmjs.com/package/@trufflesuite/bigint-buffer?activeTab=versions

##### the repo doesn't exist anymore

#### sync with github repo somehow but
1. Many packages developed by a same author are hosted in the same repo, the version for packages are not kept seperately but as a bundle
    https://github.com/babel/babel/tree/main/packages
    https://www.npmjs.com/package/@babel/core?activeTab=versions 


---

2. the tags in repo are not up-to-date, but release info is documented in some docs
- https://github.com/Stamp9/metamask-extension/blob/develop/yarn.lock#L10
- https://github.com/actions/toolkit
- https://github.com/actions/toolkit/blob/1fe633e27c4cc74616d675b71163f59f9d084381/packages/core/RELEASES.md
- https://www.npmjs.com/package/@actions/core?activeTab=versions

3. in release info, there are many packages info
- https://github.com/ethereumjs/ethereumjs-monorepo/releases
    - https://github.com/ethereumjs/ethereumjs-monorepo e.g. couldn't find @ethereumjs/common@3.1.1 in tags but can be found in some docs: https://github.com/ethereumjs/ethereumjs-monorepo/blob/869053512ebe0a7b30afd50c3f5c1ac2bd87ccac/packages/common/CHANGELOG.md?plain=1#L189 
- https://github.com/floating-ui/floating-ui/releases

4. Not maintained or sugeested not to use
- https://github.com/babel/babel-plugin-proposal-private-property-in-object




</details>


## Memo

<details open>
  <summary>Memo</summary>
  


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



**The tool structure**
1. get dep list
2. get repo list
3. report

**investigation**

[github graphql search type](https://docs.github.com/en/graphql/reference/enums#searchtype)



troubleshooting:

[Github API code search has some problems](https://github.com/orgs/community/discussions/45538)
[Forks are only indexed for code search when they have more stars than the parent repository.](https://stackoverflow.com/questions/65244853/why-does-searching-in-a-forked-repo-on-github-show-no-result-while-searching-in#:~:text=Forks%20are%20only%20indexed%20for,to%20read%20all%20the%20code.)

https://docs.github.com/en/search-github/searching-on-github/searching-code#considerations-for-code-search

https://docs.github.com/en/search-github/searching-on-github/searching-in-forks

compare:
* [Compare two commits](https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28#compare-two-commits)
* [API pagination](https://stackoverflow.com/questions/68355441/github-api-compare-2-commits-large-comparison-cant-get-all-changed-files)

npm-version
-  https://docs.npmjs.com/cli/v10/commands/npm-version#commit-hooks

renaming a repo
- https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository

collaborators
https://docs.github.com/en/rest/collaborators/collaborators?apiVersion=2022-11-28#check-if-a-user-is-a-repository-collaborator
https://docs.github.com/en/rest/collaborators/collaborators?apiVersion=2022-11-28#list-repository-collaborators
List public member for org is okay
https://docs.github.com/en/rest/orgs/members?apiVersion=2022-11-28#list-public-organization-members
https://docs.github.com/en/rest/orgs/members?apiVersion=2022-11-28#get-organization-membership-for-a-user

https://docs.github.com/en/rest/orgs/organization-roles?apiVersion=2022-11-28#list-users-that-are-assigned-to-an-organization-role
OAuth app tokens and personal access tokens (classic) need the admin:org scope to use this endpoint.


https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-user-account-settings/permission-levels-for-a-personal-account-repository
https://docs.github.com/en/rest/collaborators/collaborators?apiVersion=2022-11-28#get-repository-permissions-for-a-user

GraphQL
https://docs.github.com/zh/graphql/reference/enums#repositorypermission The access level to a repository.





GH Archive
https://www.gharchive.org/

**wallets(open sourced)**

- myetherwallet JS npm
- electrum python https://github.com/spesmilo/electrum bitcoin
- bitpay JS npm https://github.com/bitpay/wallet
- Crypto.com JS yarn https://github.com/crypto-com/chain-desktop-wallet
- Safe JS yarn v1 https://github.com/safe-global/safe-wallet-web
- Trust wallet 
- Uniswap

**dependency related**

https://owasp.org/www-project-dependency-check/

**About Socket.Dev**

Socket for GitHub

Socket watches for changes to “package manifest” files
- identify a new install script
- Telemetry
- Known Malware
- Troll Packages

https://socket.dev/npm/issue


Troll Packages -> how
The source for file explorer? github or npm?
https://socket.dev/npm/issue/gitDependency -> didn't get it


</details>

<details open>
  <summary>Endpoints</summary>
  get commits: /repos/{owner}/{repo}/commits
  find PR: /repos/{owner}/{repo}/commits/{commit_sha}/pulls
  get review info: /repos/{owner}/{repo}/pulls/{pull_number}/reviews
  check runs: /repos/{owner}/{repo}/commits/{ref}/check-runs  -> https://docs.github.com/en/rest/checks?apiVersion=2022-11-28
  PR author: https://api.github.com/search/issues?q=repo:LavaMoat/lavamoat+is:pr%20is:merged%20author:kumavis&sort=created&order=asc
  https://docs.github.com/en/search-github/getting-started-with-searching-on-github/understanding-the-search-syntax
  For API (V3) you can include the sort qualifier in your query - +sort:author-date-desc for descending and +sort:author-date-asc for ascending.
  https://api.github.com/search/repositories?q=user:km-poonacha+sort:author-date-asc

  commits
  https://api.github.com/search/commits?q=repo:LavaMoat/LavaMoat/+author:weizman+sort:author-date-asc
  PR
  https://api.github.com/search/issues?q=repo:chains-project/chains-project.github.io+is:pull-request+author:stamp9+is:merged&sort=created&order=asc

  https://api.github.com/search/issues?q=repo:LavaMoat/LavaMoat/+author:weizman+sort:author-date-asc+type:pr++is:merged
  https://api.github.com/search/issues?q=repo:LavaMoat/lavamoat+is:pr%20is:merged%20author:kumavis&sort=created&order=asc

  https://docs.github.com/en/graphql/reference/objects#pullrequestcontributionsbyrepository

  https://docs.github.com/en/graphql/reference/enums#pullrequestreviewstate
  https://docs.github.com/en/graphql/reference/enums#pullrequeststate
  https://docs.github.com/en/graphql/reference/objects#pullrequestcontributionsbyrepository
  https://docs.github.com/en/graphql/reference/objects#pullrequestreviewcontributionsbyrepository
  https://docs.github.com/en/graphql/reference/objects#commitcontributionsbyrepository

  

  CI
  https://stackoverflow.com/questions/67919168/github-checks-api-vs-check-runs-vs-check-suites
  https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#list-check-runs-for-a-git-reference

  GraphQL: https://docs.github.com/en/graphql/overview/explorer

  archived data: When a repository is archived, its issues, pull requests, code, labels, milestones, projects, wiki, releases, commits, tags, branches, reactions, code scanning alerts, comments and permissions become read-only. To make changes in an archived repository, you must unarchive the repository first.
  https://docs.github.com/en/repositories/archiving-a-github-repository/archiving-repositories


  Something fun

  - https://github.com/microsoft/pylance-release/issues/5630
  - fix: https://github.com/microsoft/pylance-release/issues/5630#issuecomment-2004637561, https://github.com/pandas-dev/pandas-stubs/pull/890


</details>

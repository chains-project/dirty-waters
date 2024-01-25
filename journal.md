Minutes 2024-01-
1. How we process patches
2. what/how should we match the related npm package version with github repo
3. do we care about the packages that are deprecated/archived?
https://github.com/trufflesuite/truffle?tab=readme-ov-file
4. want to check: the final goal is the evaluation of ssc transparency, and the tool we want to develop is here to help
5. do we only focus javascript wallets when evaluating
6. how we deal with the different package manager(yarn,different version, gradle, pnpm) problem, do we need more general method

-. thoughts：special packages / undetected packages / 


Minutes 2024-01-22
1. Tasks(repo & trace) [Steps](./steps.md)
todo:
-[] where does patches come from - exact code & authors & why

e.g. @eslint/eslintrc@patch:@eslint/eslintrc@npm%3A2.0.2#./.yarn/patches/@eslint-eslintrc-npm-2.0.2-d308674d86.patch::version=2.0.2&hash=c0def0&locator=metamask-crx%40workspace%3A.

-[] We want to know the change & author(maybe also who merge the commit) of all deps
-[] is there's anything unususal things(new contributor)


The tool we want to have:

question the tool to answer: In a new realease, who are the new contributor automatically

The final tool needs to generate a user-friendly summary


-[x] check: ledger-live @patches
ledger-live use pnpm, use `pnpm patch` & `pnpm patch-commit`, it generated the patch file authomatically
- https://github.com/LedgerHQ/ledger-live/tree/develop/patches
- https://pnpm.io/cli/patch

2. [project plan](https://docs.google.com/document/d/1JD9PU_ABYeOvAUiEkuC1EpAFavDfiO8KOAz56Uu9TEI/edit?usp=sharing)(Research question & Method & outcome)






- todo

ww45

-[x] MetaMask & Bitpay packages

-[x] 2 Paper 

ww46

-[] A method to measeaure how weak the dependencies are(rules, automated)

-[] Is there other method to extract deps?

-[] Check vuls of deps


ww49

-[x] what are the dependencies without link to a repo? why is that? what are the challenges to identify them?

-[x] how to trace each new line in a Metamask release to a specific commit and a author. write a first prototype.

# Software Supply Chain Report of MetaMask/metamask-extension - v11.1.0 &rarr; v12.9.0


<details>
    <summary>How to read the results :book: </summary>
    
 Dirty-waters has analyzed your project dependencies and found different categories for each of them:

    
 - ⚠️⚠️⚠️ : high severity 

    
 - ⚠️⚠️: medium severity 

    
 - ⚠️: low severity 

</details>
        

 ### Total packages in the supply chain: 1595

 :lock: Packages with signature changes (⚠️⚠️⚠️): 0

 :heavy_exclamation_mark: Downgraded packages (⚠️⚠️): 32

 :alien: Commits made by both New Authors and Reviewers (⚠️⚠️): 0

 :see_no_evil: Commits approved by New Reviewers (⚠️⚠️): 0

 :neutral_face: Commits made by New Authors (⚠️): 1

### Fine grained information

:dolphin: For further information about software supply chain smells in your project, take a look at the following tables.


<details>
    <summary>:heavy_exclamation_mark: Downgraded packages (⚠️⚠️) (32)</summary>
        


| package_name             | repo_link   | category           | old_version   | new_version               |
|:-------------------------|:------------|:-------------------|:--------------|:--------------------------|
| got                      |             | Downgraded package | 11.8.6        | 9.6.0                     |
| responselike             |             | Downgraded package | 2.0.1         | 1.0.2                     |
| is-plain-obj             |             | Downgraded package | 4.1.0         | 3.0.0                     |
| ci-info                  |             | Downgraded package | 3.3.2         | 2.0.0                     |
| decompress-response      |             | Downgraded package | 6.0.0         | 3.3.0                     |
| http-errors              |             | Downgraded package | 1.8.0         | 1.6.3                     |
| balanced-match           |             | Downgraded package | 1.0.2         | 0.4.2                     |
| @szmarczak/http-timer    |             | Downgraded package | 4.0.6         | 1.1.2                     |
| has-flag                 |             | Downgraded package | 4.0.0         | 1.0.0                     |
| defer-to-connect         |             | Downgraded package | 2.0.1         | 1.1.3                     |
| memoize-one              |             | Downgraded package | 6.0.0         | 5.2.1                     |
| node-fetch               |             | Downgraded package | 3.3.1         | 2.7.0                     |
| ip                       |             | Downgraded package | 2.0.0         | 1.1.8                     |
| @babel/preset-modules    |             | Downgraded package | 0.1.5         | 0.1.6-no-external-plugins |
| @ethersproject/web       |             | Downgraded package | 5.7.1         | 5.7.0                     |
| normalize-url            |             | Downgraded package | 6.1.0         | 4.5.1                     |
| setprototypeof           |             | Downgraded package | 1.2.0         | 1.1.0                     |
| keyv                     |             | Downgraded package | 4.5.0         | 3.1.0                     |
| supports-color           |             | Downgraded package | 8.1.1         | 3.2.3                     |
| @ethersproject/networks  |             | Downgraded package | 5.7.1         | 5.7.0                     |
| json-buffer              |             | Downgraded package | 3.0.1         | 3.0.0                     |
| @ethersproject/providers |             | Downgraded package | 5.7.2         | 5.7.0                     |
| js-base64                |             | Downgraded package | 3.6.1         | 2.6.4                     |
| get-stream               |             | Downgraded package | 6.0.1         | 4.1.0                     |
| p-cancelable             |             | Downgraded package | 2.1.1         | 1.1.0                     |
| cacheable-request        |             | Downgraded package | 7.0.2         | 6.1.0                     |
| portfinder               |             | Downgraded package | 1.0.32        | 1.0.28                    |
| replace-ext              |             | Downgraded package | 2.0.0         | 1.0.1                     |
| path-to-regexp           |             | Downgraded package | 2.2.1         | 1.9.0                     |
| @sindresorhus/is         |             | Downgraded package | 4.6.0         | 0.14.0                    |
| ini                      |             | Downgraded package | 3.0.0         | 2.0.0                     |
| ansi-styles              |             | Downgraded package | 6.2.1         | 2.2.1                     |
</details>


<details>
    <summary>:neutral_face: Commits made by New Authors (⚠️) (1)</summary>
        


| sha                                      | package_name                                                                                                                             | repo_name                   | old_version   | new_version   | author_first   | merger   | prr_first   | reviewer    | reviewer_type   |   package_number | repo_link   | category   | signature_changes   |
|:-----------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------|:----------------------------|:--------------|:--------------|:---------------|:---------|:------------|:------------|:----------------|-----------------:|:------------|:-----------|:--------------------|
| 45c17172f3b29f1d9aea29afc84db25fb9300f45 | ['lavamoat-core@patch:lavamoat-core@npm%3A15.1.1#~/.yarn/patches/lavamoat-core-npm-15.1.1-51fbe39988.patch::version=15.1.1&hash=95165a'] | MetaMask/metamask-extension |               |               | True           | Gudahtt  | False       | brad-decker | User            |                1 |             |            |                     |
</details>

### Call to Action:

                      
<details>
    <summary>👻What do I do now? </summary>
        For packages with signature changes:  

        This means that a dependency either had code signature and now does not, or that the signature was valid and now it's not.
        This could be a security risk, and you should halt the project until you can verify the changes. 

        
For downgraded dependencies:  

        1. Check the release notes of the new version to see if the downgrade is intentional. If the new version is more than one release ahead, verify whether any breaking changes in between apply to your project.
        2. If the downgrade is unintentional, consider updating the package to a version that is compatible with your project.
        
For commits made by both new authors and reviewers:  

        1. Verify, as best as you can, that the new authors and reviewers are not malicious actors.
        2. If you are unsure, consider reverting the changes.
        
For commits approved by new reviewers:  

        Verify, as best as you can, that the new reviewers are not malicious actors.
        
For commits made by new authors:  

        Verify, as best as you can, that the new authors are not malicious actors.
        The fact that the reviewers are not new to the repository is a good sign.
</details>



---

Report created by [dirty-waters](https://github.com/chains-project/dirty-waters/).

Report created on 2025-03-01 21:29:57
- Tool version: 7e806c5d
- Project Name: MetaMask/metamask-extension
- Compared project versions: v11.1.0 & v12.9.0

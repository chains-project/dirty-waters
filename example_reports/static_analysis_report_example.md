# Software Supply Chain Report of abc/xyz - vd.e.f

This report is a gradual report: that is, only the highest severity smell type with issues found within this project is reported.
Gradual reports are enabled by default. You can disable this feature, and get a full report, by using the `--no-gradual-report` flag.

All available checks were performed.

---

<details>
    <summary>How to read the results :book: </summary>
    
 Dirty-waters has analyzed your project dependencies and found different categories for each of them:

- ⚠️⚠️⚠️ : high severity
- ⚠️⚠️: medium severity
- ⚠️: low severity

</details>

### Total packages in the supply chain: 432

:heavy_exclamation_mark: Packages with no source code URL (⚠️⚠️⚠️) 5

:no_entry: Packages with repo URL that is 404 (⚠️⚠️⚠️) 1

:wrench: Packages with inaccessible GitHub tag (⚠️⚠️) 60

:cactus: Packages that are forks (⚠️⚠️) 3

:lock: Packages without code signature (⚠️⚠️) 17

<details>
    <summary>Other info:</summary>
    
- Source code repo is not hosted on GitHub:  95

    This could be due to the package being hosted on a different platform or the package not having a source code repo.

</details>
                            
                            
### Fine grained information

:dolphin: For further information about software supply chain smells in your project, take a look at the following tables.

<details>
<summary>Source code links that could not be found(6)</summary>

| index | package_name                                  | github_url                    | github_exists |
| ----: | :-------------------------------------------- | :---------------------------- | :------------ |
|     1 | org.sonatype.sisu:sisu-guice@noaop            | No_repo_info_found            |               |
|     2 | org.sonatype.plexus:plexus-sec-dispatcher@1.3 | No_repo_info_found            |               |
|     3 | org.sonatype.plexus:plexus-cipher@1.4         | No_repo_info_found            |               |
|     4 | org.sonatype.sisu:sisu-guice@no_aop           | No_repo_info_found            |               |
|     5 | com.google.inject:guice@no_aop                | No_repo_info_found            |               |
|     6 | org.iq80.snappy:snappy@0.4                    | https://github.com/dain/snapy | False         |

</details>

### Call to Action:

<details>
    <summary>👻What do I do now? </summary>
        For packages without source code & accessible release tags:

        Pull Request to the maintainer of dependency, requesting correct repository metadata and proper tagging.

For deprecated packages:

        1. Confirm the maintainer’s deprecation intention
        2. Check for not deprecated versions

For packages without provenance:

        Open an issue in the dependency’s repository to request the inclusion of provenance and build attestation in the CI/CD pipeline.

For packages that are forks

        Inspect the package and its GitHub repository to verify the fork is not malicious.

For packages without code signature:

        Open an issue in the dependency’s repository to request the inclusion of code signature in the CI/CD pipeline.

For packages with invalid code signature:

        It's recommended to verify the code signature and contact the maintainer to fix the issue.

</details>

---

Report created by [dirty-waters](https://github.com/chains-project/dirty-waters/).

Report created on 2025-02-10 23:13:43

- Tool version: 82f1cb0a
- Project Name: abc/xyz
- Project Version: vd.e.f

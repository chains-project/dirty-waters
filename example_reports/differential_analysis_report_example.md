# Software Supply Chain Report of abc/xyz - vd.e.f &rarr; vd.g.h

This report is a gradual report: that is, only the highest severity smell type with issues found within this project is reported.
Gradual reports are enabled by default. You can disable this feature, and get a full report, by setting the `--gradual-report` flag to `false`.

:lock: Packages with signature changes (⚠️⚠️⚠️): (0)

:heavy_exclamation_mark: Downgraded packages (⚠️⚠️): (1)

:alien: Commits made by both New Authors and Reviewers (⚠️⚠️): (0)

:see_no_evil: Commits approved by New Reviewers (⚠️⚠️): (3)

:neutral_face: Commits made by New Authors (⚠️): (42)

### Fine grained information

:dolphin: For further information about software supply chain smells in your project, take a look at the following tables.

<details>
    <summary>:heavy_exclamation_mark: Downgraded packages (⚠️⚠️) (1)</summary>

| package_name               | repo_link                            | category           | old_version | new_version |
| :------------------------- | :----------------------------------- | :----------------- | :---------- | :---------- |
| com.thoughtworks.qdox:qdox | https://github.com/paul-hammant/qdox | Downgraded package | 2.2.0       | 2.1.0       |

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

Report created on 2025-02-10 23:13:48

- Tool version: 82f1cb0a
- Project Name: abc/xyz
- Compared project versions: vd.e.f & vd.g.h

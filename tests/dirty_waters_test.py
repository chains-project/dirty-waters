import pytest
import subprocess
import re
from pathlib import Path
from typing import Tuple, Dict
import sys
from markdown_it import MarkdownIt


class SmellParser:
    """Parse and extract smell counts and information from tool output."""

    @staticmethod
    def extract_smells(output: str, diff_analysis: bool = False) -> Dict[str, int]:
        """
        Extract smell information from the output string.
        Returns a dictionary with counts for each type of smell.
        """
        if not diff_analysis:
            matches = {
                "no_source_code": re.search(
                    r":heavy_exclamation_mark: Packages with no source code URL \(⚠️⚠️⚠️\): (\d+)", output
                ),
                "not_found": re.search(r":no_entry: Packages with repo URL that is 404 \(⚠️⚠️⚠️\): (\d+)", output),
                "inaccessible_tag": re.search(r":wrench: Packages with inaccessible GitHub tag \(⚠️⚠️\): (\d+)", output),
                "forked_project": re.search(r":cactus: Packages that are forks \(⚠️⚠️\): (\d+)", output),
                "no_code_signature": re.search(r":lock: Packages without code signature \(⚠️⚠️\): (\d+)", output),
                "deprecated": re.search(r":x: Packages that are deprecated \(⚠️⚠️\): (\d+)", output),
                "no_provenance": re.search(
                    r":black_square_button: Packages without build attestation \(⚠️\): (\d+)", output
                ),
            }
        else:
            matches = {
                "signature_changes": re.search(r":lock: Packages with signature changes \(⚠️⚠️⚠️\): (\d+)", output),
                "downgraded_dependencies": re.search(
                    r":heavy_exclamation_mark: Downgraded packages \(⚠️⚠️\): (\d+)", output
                ),
                "both_new": re.search(r":alien: Commits made by both New Authors and Reviewers \(⚠️⚠️\): (\d+)", output),
                "new_reviewer": re.search(r":see_no_evil: Commits approved by New Reviewers \(⚠️⚠️\): (\d+)", output),
                "new_author": re.search(r":neutral_face: Commits made by New Authors \(⚠️\): (\d+)", output),
            }

        smells = {smell: int(amount.group(1)) if amount else 0 for smell, amount in matches.items()}
        return smells


def run_tool_cli(
    project: str,
    version: str = None,
    diff_version: str = None,
    package_manager: str = "maven",
    gradual_report: bool = False,
    pnpm_scope: str = None,
) -> str:
    """
    Run the tool as a CLI command and return output.
    """
    # Base command; sys.executable is the Python interpreter used to run this script
    cmd = [sys.executable, "tool/main.py", "-p", project]

    if diff_version:
        cmd.extend(["-d", "-v", version, "-vn", diff_version])
    else:
        cmd.extend(["-v", version])

    if package_manager == "pnpm" and pnpm_scope:
        cmd.extend(["--pnpm-scope", pnpm_scope])

    if not gradual_report:
        cmd.append("--no-gradual-report")

    cmd.extend(["-pm", package_manager])

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if diff_version:
            output_file = re.search(r"Report from differential analysis generated at (.+)", result.stdout).group(1)
        else:
            output_file = re.search(r"Report from static analysis generated at (.+)", result.stdout).group(1)
        return Path(output_file).read_text(), output_file
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stdout}\n{e.stderr}")
        return f"Error: {e.stdout}\n{e.stderr}"


class TestSmellDetection:
    @pytest.fixture
    def expected_outputs(self):
        """
        Fixture to load expected outputs from files.
        Place your expected output files in tests/expected_outputs/
        """
        expected_dir = Path("tests/expected_outputs")
        return {
            "single_maven_spoon": (expected_dir / "spoon_v11.1.0.md").read_text(),
            "diff_maven_spoon": (expected_dir / "spoon_v11.1.1-beta-2_v11.1.1-beta-9_diff.md").read_text(),
            "single_yarn_berry": (expected_dir / "metamask_v11.10.0.md").read_text(),
            "diff_yarn_berry": (expected_dir / "metamask_v11.1.0_v12.9.0_diff.md").read_text(),
            # TODO: missing expected outputs for the ones below
            # "single_yarn_classic": (expected_dir / "webpack_v5.98.0.md").read_text(),
            # "diff_yarn_classic": (expected_dir / "webpack_v5.50.0_v5.98.0_diff.md").read_text(),
            # "single_npm": (expected_dir / "gatsby_v5.14.0.md").read_text(),
            # "diff_npm": (expected_dir / "gatsby_v5.1.0_v5.14.0_diff.md").read_text(),
            # "single_pnpm": (expected_dir / "ledger-live-desktop_2.100.0.md").read_text(),
            # "diff_pnpm": (expected_dir / "ledger-live-desktop_2.95.0_2.100.0_diff.md").read_text(),
            # "single_maven_sbom_exe": (expected_dir / "sbom_exe_v0.14.1.md").read_text(),
            # "diff_maven_sbom_exe": (expected_dir / "sbom_exe_v0.13.0_v0.14.1_diff.md").read_text(),
            # TODO: add expected outputs, and tests, for gradual report
            # TODO: add expected outputs, and tests, for enabling specific smell checks
        }

    def test_static_maven_spoon(self, expected_outputs):
        """Test outputs coming from static analysis, for Maven, for Spoon."""
        # Run tool
        actual_output, output_file = run_tool_cli(project="INRIA/spoon", version="v11.1.0", package_manager="maven")

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output)
        expected_smells = parser.extract_smells(expected_outputs["single_maven_spoon"])

        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for Spoon v11.1.0:\nExpected: {expected_smells}\nGot: {actual_smells}"

        print(f"Static Analysis Output file path: {output_file}")

    @pytest.mark.skip(reason="Expected output not acquired yet")
    def test_static_maven_sbom_exe(self, expected_outputs):
        """Test outputs coming from static analysis, for Maven, for sbom.exe."""
        # Run tool
        actual_output, output_file = run_tool_cli(project="chains-project/sbom.exe", version="v0.14.1", package_manager="maven")

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output)
        expected_smells = parser.extract_smells(expected_outputs["single_maven_sbom_exe"])

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for sbom.exe v0.14.1:\nExpected: {expected_smells}\nGot: {actual_smells}"

    @pytest.mark.skip(reason="Expected output not acquired yet")
    def test_static_npm(self, expected_outputs):
        """Test outputs coming from static analysis, for NPM."""
        # Run tool
        actual_output, output_file = run_tool_cli(project="gatsbyjs/gatsby", version="v5.14.0", package_manager="npm")

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output)
        expected_smells = parser.extract_smells(expected_outputs["single_npm"])

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for Gatsby v5.14.0:\nExpected: {expected_smells}\nGot: {actual_smells}"

    @pytest.mark.skip(reason="Expected output not acquired yet")
    def test_static_yarn_classic(self, expected_outputs):
        """Test outputs coming from static analysis, for Yarn Classic."""
        # Run tool
        actual_output, output_file = run_tool_cli(project="webpack/webpack", version="v5.98.0", package_manager="yarn-classic")

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output)
        expected_smells = parser.extract_smells(expected_outputs["single_yarn_classic"])

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for Webpack v5.98.0:\nExpected: {expected_smells}\nGot: {actual_smells}"

    def test_static_yarn_berry(self, expected_outputs):
        """Test outputs coming from static analysis, for Yarn Berry."""
        # Run tool
        actual_output, output_file = run_tool_cli(
            project="MetaMask/metamask-extension", version="v11.10.0", package_manager="yarn-berry"
        )

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output)
        expected_smells = parser.extract_smells(expected_outputs["single_yarn_berry"])

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for MetaMask v11.10.0:\nExpected: {expected_smells}\nGot: {actual_smells}"

    @pytest.mark.skip(reason="Expected output not acquired yet")
    def test_static_pnpm(self, expected_outputs):
        """Test outputs coming from static analysis, for PNPM."""
        # Run tool
        actual_output, output_file = run_tool_cli(
            project="LedgerHQ/ledger-live",
            version="@ledgerhq/live-desktop@2.100.0",
            package_manager="pnpm",
            pnpm_scope="ledger-live-desktop",
        )

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output)
        expected_smells = parser.extract_smells(expected_outputs["single_pnpm"])

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for Ledger Live Desktop @2.100.0:\nExpected: {expected_smells}\nGot: {actual_smells}"

    def test_diff_maven_spoon(self, expected_outputs):
        """Test outputs coming from diff analysis, for Maven, for Spoon."""
        # Run tool
        actual_output, output_file = run_tool_cli(
            project="INRIA/spoon", version="v11.1.1-beta-2", diff_version="v11.1.1-beta-9", package_manager="maven"
        )

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output, diff_analysis=True)
        expected_smells = parser.extract_smells(expected_outputs["diff_maven_spoon"], diff_analysis=True)

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for Spoon v11.1.1-beta-2 vs v11.1.1-beta-9:\nExpected: {expected_smells}\nGot: {actual_smells}"

        print(f"Differential Analysis Output file path: {output_file}")

    @pytest.mark.skip(reason="Expected output not acquired yet")
    def test_diff_maven_sbom_exe(self, expected_outputs):
        """Test outputs coming from diff analysis, for Maven, for sbom.exe."""
        # Run tool
        actual_output, output_file = run_tool_cli(
            project="chains-project/sbom.exe", version="v0.13.0", diff_version="v0.14.1", package_manager="maven"
        )

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output, diff_analysis=True)
        expected_smells = parser.extract_smells(expected_outputs["diff_maven_sbom_exe"], diff_analysis=True)

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for sbom.exe v0.13.0 vs v0.14.1:\nExpected: {expected_smells}\nGot: {actual_smells}"

    @pytest.mark.skip(reason="Expected output not acquired yet")
    def test_diff_npm(self, expected_outputs):
        """Test outputs coming from diff analysis, for NPM."""
        # Run tool
        actual_output, output_file = run_tool_cli(
            project="gatsbyjs/gatsby", version="v5.1.0", diff_version="v5.14.0", package_manager="npm"
        )

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output, diff_analysis=True)
        expected_smells = parser.extract_smells(expected_outputs["diff_npm"], diff_analysis=True)

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for Gatsby v5.1.0 vs v5.14.0:\nExpected: {expected_smells}\nGot: {actual_smells}"

    @pytest.mark.skip(reason="Expected output not acquired yet")
    def test_diff_yarn_classic(self, expected_outputs):
        """Test outputs coming from diff analysis, for Yarn Classic."""
        # Run tool
        actual_output, output_file = run_tool_cli(
            project="webpack/webpack", version="v5.50.0", diff_version="v5.98.0", package_manager="yarn-classic"
        )

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output, diff_analysis=True)
        expected_smells = parser.extract_smells(expected_outputs["diff_yarn_classic"], diff_analysis=True)

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for Webpack v5.50.0 vs v5.98.0:\nExpected: {expected_smells}\nGot: {actual_smells}"

    def test_diff_yarn_berry(self, expected_outputs):
        """Test outputs coming from diff analysis, for Yarn Berry."""
        # Run tool
        actual_output, output_file = run_tool_cli(
            project="MetaMask/metamask-extension",
            version="v11.1.0",
            diff_version="v12.9.0",
            package_manager="yarn-berry",
        )

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output, diff_analysis=True)
        expected_smells = parser.extract_smells(expected_outputs["diff_yarn_berry"], diff_analysis=True)

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for MetaMask v11.1.0 vs v12.9.0:\nExpected: {expected_smells}\nGot: {actual_smells}"

    @pytest.mark.skip(reason="Expected output not acquired yet")
    def test_diff_pnpm(self, expected_outputs):
        """Test outputs coming from diff analysis, for PNPM."""
        # Run tool
        actual_output, output_file = run_tool_cli(
            project="LedgerHQ/ledger-live",
            version="@ledgerhq/live-desktop@2.99.0",
            diff_version="@ledgerhq/live-desktop@2.100.0",
            package_manager="pnpm",
            pnpm_scope="ledger-live-desktop",
        )

        # Parse smells
        parser = SmellParser()
        actual_smells = parser.extract_smells(actual_output, diff_analysis=True)
        expected_smells = parser.extract_smells(expected_outputs["diff_pnpm"], diff_analysis=True)

        # Compare smells
        assert (
            actual_smells == expected_smells
        ), f"Output mismatch for Ledger Live Desktop @2.99.0 vs @2.100.0:\nExpected: {expected_smells}\nGot: {actual_smells}"

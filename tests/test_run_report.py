"""The README results block is regenerated between markers without touching the rest."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_report.py"
spec = importlib.util.spec_from_file_location("run_report", SCRIPT)
run_report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_report)


def test_report_for_readme_demotes_headings_and_fixes_figures():
    md = "# Title\n\n## 1. Stats\n\n### Sub\n\n![eq](figures/a.png)\n"
    out = run_report.report_for_readme(md, "reports/x/figures")
    assert "# Title" not in out
    assert "### 1. Stats" in out and "#### Sub" in out
    assert "](reports/x/figures/a.png)" in out


def test_inject_replaces_only_the_block():
    readme = f"intro\n{run_report.START}\nold\n{run_report.END}\noutro\n"
    new = run_report.inject(readme, "NEW")
    assert new.startswith("intro\n") and new.endswith("outro\n")
    assert "old" not in new and "NEW" in new
    assert run_report.inject(new, "NEWER").count(run_report.START) == 1


def test_readme_contains_generated_results():
    readme = (SCRIPT.parents[1] / "README.md").read_text()
    block = readme.split(run_report.START)[1].split(run_report.END)[0]
    assert "Is the edge distinguishable from zero?" in block

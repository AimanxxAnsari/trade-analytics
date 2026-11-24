"""The walkthrough notebook must execute end to end (guards against silent rot)."""

from pathlib import Path

import nbformat
from nbclient import NotebookClient

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "pillar1_walkthrough.ipynb"


def test_walkthrough_notebook_executes():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    NotebookClient(
        nb,
        timeout=600,
        kernel_name="python3",
        resources={"metadata": {"path": str(NOTEBOOK.parent)}},
    ).execute()
    errors = [
        o
        for c in nb.cells
        if c.cell_type == "code"
        for o in c.outputs
        if o.get("output_type") == "error"
    ]
    assert not errors

"""Validate repository-local CLI output paths before any execution begins."""
import argparse
from pathlib import Path


def repository_output_path(value, root):
    """Resolve relative paths from cwd and reject paths outside the evidence root."""
    target = Path(value).expanduser().resolve()
    try:
        target.relative_to(Path(root).resolve())
    except ValueError:
        raise argparse.ArgumentTypeError("--out must resolve inside the repository") from None
    return target

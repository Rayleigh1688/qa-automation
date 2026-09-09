#!/usr/bin/env python3
"""Export reusable runtime sources without FILBET business code or local data."""
import argparse
from qa_core.export import export_runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, help='New destination directory; must not exist')
    args = parser.parse_args()
    try:
        manifest = export_runtime(args.out)
    except (OSError, ValueError):
        parser.exit(2, 'Export failed: check source files, destination permissions and that --out does not exist.\n')
    print(f'Exported {len(manifest["files"])} runtime files with SHA256 manifest.')


if __name__ == '__main__':
    main()

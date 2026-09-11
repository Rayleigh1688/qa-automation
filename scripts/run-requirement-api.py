#!/usr/bin/env python3
"""Validate/run requirement-owned API combinations independently of P0."""
import argparse
from filbet.requirement_api import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('requirements', nargs='+')
    parser.add_argument('--env')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--insecure', action='store_true')
    parser.add_argument('--timeout', type=float, default=15)
    parser.add_argument('--only', nargs='+', help='Run named combinations only; retains separate retest evidence')
    parser.set_defaults(body_format='cbor')
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, OSError, KeyError) as error:
        print('Preflight failed:', type(error).__name__, '(check suite structure and environment)')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

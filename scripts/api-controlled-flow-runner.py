#!/usr/bin/env python3
"""Compatibility CLI for FILBET controlled operations."""
from filbet.controlled import ControlledFlow


def main():
    ControlledFlow().execute()


if __name__ == '__main__':
    main()

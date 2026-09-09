#!/usr/bin/env python3
"""Compatibility entry point for the FILBET smoke runner."""
from filbet import smoke as _implementation

globals().update({name: value for name, value in vars(_implementation).items() if not name.startswith('__')})

if __name__ == '__main__':
    main()

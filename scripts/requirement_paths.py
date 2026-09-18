"""Project requirement locations; explicit IDs include archives, discovery defaults active."""
from pathlib import Path
import re


def requirement_dir(root, story):
    if not re.fullmatch(r'ISOP-\d+', story):
        raise ValueError('invalid requirement identifier')
    base = Path(root) / 'requirements'
    current = base / story
    matches = ([current] if current.is_dir() else []) + sorted(
        p for p in (base / 'history').glob('*/' + story) if p.is_dir())
    if len(matches) > 1:
        raise ValueError('duplicate requirement directories: ' + story)
    return matches[0] if matches else current


def requirement_dirs(root, *, include_history=False):
    base = Path(root) / 'requirements'
    paths = list(base.glob('ISOP-*'))
    if include_history:
        paths.extend((base / 'history').glob('*/ISOP-*'))
    result = sorted(p for p in paths if p.is_dir() and re.fullmatch(r'ISOP-\d+', p.name))
    if len({p.name for p in result}) != len(result):
        raise ValueError('duplicate requirement directories')
    return result


def is_archived(root, story):
    return requirement_dir(root, story).parent != Path(root) / 'requirements'

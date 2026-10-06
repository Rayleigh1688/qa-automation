"""Bounded, offline Xmind ZIP I/O, without extracting archive paths.

The JSON layout follows xmindltd/xmind-sdk-js (src/utils/zipper.ts) and
xmindltd/xmind-viewer (example/content.json). Classic XML follows the official
xmind-sdk-python content:2.0 model. Unknown JSON and ZIP resources survive a
round trip. Classic XML edits deliberately support only a conservative subset.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any
from xml.dom import Node, minidom
from xml.parsers import expat
import zipfile
import zlib


RIGHT_STRUCTURE = 'org.xmind.ui.logic.right'
CONTENT_NAMESPACE = 'urn:xmind:xmap:xmlns:content:2.0'
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_ENTRY_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = 2048
MAX_TOPICS = 50000
MAX_DEPTH = 128
MAX_XML_NODES = 200000


@dataclass
class XmindDocument:
    sheets: list[dict]
    entries: dict[str, bytes]
    format: str


def _json(data: bytes, filename: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'{filename}: duplicate JSON key {key!r}')
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f'{filename}: invalid JSON number {value}')

    try:
        return json.loads(data.decode('utf-8-sig'), object_pairs_hook=pairs,
                          parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f'{filename}: invalid JSON') from exc


def _entry_name(name: str) -> None:
    path = PurePosixPath(name)
    if (not name or '\x00' in name or '\\' in name or path.is_absolute()
            or '..' in path.parts or re.match(r'^[A-Za-z]:', name)):
        raise ValueError('Xmind archive contains an unsafe entry name')


def _check_entries(entries: dict[str, bytes]) -> None:
    if len(entries) > MAX_ENTRIES:
        raise ValueError('Xmind archive has too many entries')
    total = 0
    for name, data in entries.items():
        _entry_name(name)
        if not isinstance(data, bytes):
            raise ValueError('Xmind archive entry must contain bytes')
        if len(data) > MAX_ENTRY_BYTES:
            raise ValueError('Xmind archive entry exceeds the size limit')
        total += len(data)
    if total > MAX_TOTAL_BYTES:
        raise ValueError('Xmind archive exceeds the uncompressed size limit')


def _normalize_sheets(raw: Any) -> list[dict]:
    if not isinstance(raw, list) or not raw:
        raise ValueError('Xmind content must be a nonempty list of sheets')
    ids = set()
    count = 0

    def identity(item, kind):
        if not isinstance(item, dict):
            raise ValueError(f'Xmind {kind} must be an object')
        key = item.get('id')
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f'Xmind {kind} requires a nonempty string id')
        if key in ids:
            raise ValueError(f'Xmind content contains duplicate id {key!r}')
        ids.add(key)
        if not isinstance(item.get('title', ''), str):
            raise ValueError(f'Xmind {kind} title must be a string')

    def topic(item, depth):
        nonlocal count
        if depth > MAX_DEPTH:
            raise ValueError('Xmind topic depth exceeds the limit')
        count += 1
        if count > MAX_TOPICS:
            raise ValueError('Xmind topic count exceeds the limit')
        identity(item, 'topic')
        result = dict(item)
        result.setdefault('title', '')
        for key in ('structureClass', 'href'):
            if key in item and not isinstance(item[key], str):
                raise ValueError(f'Xmind topic {key} must be a string')
        children = item.get('children', {})
        if not isinstance(children, dict):
            raise ValueError('Xmind topic children must be an object')
        result['children'] = {}
        for kind, nodes in children.items():
            if not isinstance(nodes, list):
                raise ValueError('Xmind child topic groups must be lists')
            result['children'][kind] = [topic(child, depth + 1) for child in nodes]
        result['children'].setdefault('attached', [])
        notes = item.get('notes', {})
        if not isinstance(notes, dict):
            raise ValueError('Xmind topic notes must be an object')
        result['notes'] = dict(notes)
        plain = notes.get('plain', {})
        if not isinstance(plain, dict) or not isinstance(plain.get('content', ''), str):
            raise ValueError('Xmind plain notes content must be a string')
        result['notes']['plain'] = dict(plain)
        result['notes']['plain'].setdefault('content', '')
        labels = item.get('labels', [])
        # Old SDK models also accepted a single label string.
        if isinstance(labels, str):
            labels = [labels]
        if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
            raise ValueError('Xmind labels must be strings')
        result['labels'] = list(labels)
        markers = item.get('markers', [])
        if not isinstance(markers, list) or not all(
                isinstance(marker, dict) and isinstance(marker.get('markerId'), str)
                and marker['markerId'] for marker in markers):
            raise ValueError('Xmind markers require string markerId values')
        result['markers'] = [dict(marker) for marker in markers]
        return result

    sheets = []
    for sheet in raw:
        identity(sheet, 'sheet')
        result = dict(sheet)
        result.setdefault('title', '')
        result['rootTopic'] = topic(sheet.get('rootTopic'), 0)
        sheets.append(result)
    try:
        return copy.deepcopy(sheets)
    except RecursionError as exc:
        raise ValueError('Xmind content nesting exceeds the limit') from exc


def _validate_xml(data: bytes, filename: str) -> None:
    # Reject DTD declarations before parsing, including UTF-16/32 documents.
    if re.search(br'<!\s*(?:DOCTYPE|ENTITY)\b', data.replace(b'\x00', b''), re.I):
        raise ValueError(f'{filename}: XML entities and DTDs are unsupported')
    # Bound arbitrary XML subtrees too, before allocating the full editable DOM.
    nodes = 1  # The document node; attributes also allocate a text child in minidom.
    depth = 0

    def start(name, attrs):
        nonlocal nodes, depth
        nodes += 1 + 2 * len(attrs)
        depth += 1
        if nodes > MAX_XML_NODES or depth > MAX_DEPTH * 4:
            raise ValueError(f'{filename}: XML nesting or node count exceeds the limit')

    def node(*args):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_XML_NODES:
            raise ValueError(f'{filename}: XML node count exceeds the limit')

    def text(data):
        if data:
            # Counting each parser callback conservatively bounds coalesced DOM text.
            node()

    def end(name):
        nonlocal depth
        depth -= 1

    def forbidden(*args):
        raise ValueError(f'{filename}: XML entities and DTDs are unsupported')

    try:
        parser = expat.ParserCreate()
        parser.StartElementHandler = start
        parser.EndElementHandler = end
        parser.CommentHandler = node
        parser.ProcessingInstructionHandler = node
        parser.CharacterDataHandler = text
        parser.StartDoctypeDeclHandler = forbidden
        parser.EntityDeclHandler = forbidden
        parser.ExternalEntityRefHandler = forbidden
        parser.Parse(data, True)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f'{filename}: invalid XML') from exc


def _xml(data: bytes, filename: str) -> minidom.Document:
    _validate_xml(data, filename)
    try:
        return minidom.parseString(data)
    except Exception as exc:
        raise ValueError(f'{filename}: invalid XML') from exc


def _elements(node, name=None):
    return [child for child in node.childNodes if child.nodeType == Node.ELEMENT_NODE
            and (name is None or (child.localName == name and child.namespaceURI == CONTENT_NAMESPACE))]


def _one(node, name):
    found = _elements(node, name)
    if len(found) > 1:
        raise ValueError(f'Xmind XML has duplicate {name} elements')
    return found[0] if found else None


def _text(node):
    if node is None:
        return ''
    return ''.join(child.data if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE)
                   else _text(child) for child in node.childNodes)


def _xml_sheets(dom):
    root = dom.documentElement
    if root.localName != 'xmap-content' or root.namespaceURI != CONTENT_NAMESPACE:
        raise ValueError('Unsupported Xmind XML content namespace or root element')

    def topic(node, depth):
        if depth > MAX_DEPTH:
            raise ValueError('Xmind topic depth exceeds the limit')
        result = {'id': node.getAttribute('id'), 'title': _text(_one(node, 'title'))}
        if node.hasAttribute('structure-class'):
            result['structureClass'] = node.getAttribute('structure-class')
        if node.hasAttributeNS('http://www.w3.org/1999/xlink', 'href'):
            result['href'] = node.getAttributeNS('http://www.w3.org/1999/xlink', 'href')
        children = _one(node, 'children')
        groups = {}
        if children is not None:
            for group in _elements(children, 'topics'):
                kind = group.getAttribute('type')
                if not kind or kind in groups:
                    raise ValueError('Xmind XML has invalid or duplicate topic groups')
                groups[kind] = [topic(child, depth + 1) for child in _elements(group, 'topic')]
        result['children'] = groups
        notes = _one(node, 'notes')
        result['notes'] = {'plain': {'content': _text(_one(notes, 'plain')) if notes else ''}}
        labels = _one(node, 'labels')
        result['labels'] = [_text(label) for label in _elements(labels, 'label')] if labels else []
        refs = _one(node, 'marker-refs')
        result['markers'] = [{'markerId': ref.getAttribute('marker-id')}
                             for ref in _elements(refs, 'marker-ref')] if refs else []
        return result

    result = []
    for sheet in _elements(root, 'sheet'):
        roots = _elements(sheet, 'topic')
        if len(roots) != 1:
            raise ValueError('Classic Xmind sheet must have exactly one root topic')
        result.append({'id': sheet.getAttribute('id'), 'title': _text(_one(sheet, 'title')),
                       'rootTopic': topic(roots[0], 0)})
    return _normalize_sheets(result)


def read_xmind(path: str | Path) -> XmindDocument:
    """Read modern JSON or classic XML Xmind content and all ZIP resources."""
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_ARCHIVE_BYTES + 1)
    return read_xmind_bytes(data)


def read_xmind_bytes(data: bytes) -> XmindDocument:
    """Parse one bounded byte snapshot, also usable for provenance hashing."""
    if not isinstance(data, bytes):
        raise ValueError('Xmind archive data must be bytes')
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError('Xmind archive exceeds the compressed size limit')
    entries = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ENTRIES:
                raise ValueError('Xmind archive has too many entries')
            total = 0
            for info in infos:
                _entry_name(info.filename)
                if info.filename in entries:
                    raise ValueError('Xmind archive contains duplicate entry names')
                if info.flag_bits & 1:
                    raise ValueError('Encrypted Xmind archives are unsupported')
                if info.file_size > MAX_ENTRY_BYTES:
                    raise ValueError('Xmind archive entry exceeds the size limit')
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    raise ValueError('Xmind archive exceeds the uncompressed size limit')
                entries[info.filename] = archive.read(info)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error) as exc:
        raise ValueError('Invalid or unsupported Xmind ZIP archive') from exc
    _check_entries(entries)
    if 'content.json' in entries:
        return XmindDocument(_normalize_sheets(_json(entries['content.json'], 'content.json')),
                             entries, 'json')
    if 'content.xml' in entries:
        dom = _xml(entries['content.xml'], 'content.xml')
        try:
            sheets = _xml_sheets(dom)
        finally:
            dom.unlink()
        return XmindDocument(sheets, entries, 'xml')
    raise ValueError('Xmind archive has neither content.json nor content.xml')


def _thumbnail(name):
    path = PurePosixPath(name)
    return (bool(path.parts and path.parts[0].lower() == 'thumbnails')
            or (len(path.parts) == 1 and path.name.lower().startswith('thumbnail.')))


def _encode_json(value):
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError('Xmind content must be serializable JSON') from exc


def _classic_content(sheets, data):
    dom = _xml(data, 'content.xml')
    try:
        old = _xml_sheets(dom)
        if [sheet['id'] for sheet in sheets] != [sheet['id'] for sheet in old]:
            raise ValueError('Classic XML write cannot add, remove, or reorder sheets safely')

        def create(parent, local_name):
            prefix = parent.prefix
            name = f'{prefix}:{local_name}' if prefix else local_name
            return dom.createElementNS(CONTENT_NAMESPACE, name)

        def set_text(parent, name, value):
            element = _one(parent, name)
            if element is None:
                element = create(parent, name)
                parent.appendChild(element)
            if _elements(element):
                raise ValueError(f'Classic XML cannot replace rich {name} safely')
            for child in list(element.childNodes):
                if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
                    element.removeChild(child)
            element.appendChild(dom.createTextNode(value))

        def topic(node, before, after):
            allowed = {'id', 'title', 'class', 'structureClass', 'children', 'notes', 'labels', 'markers', 'href'}
            if set(after) - allowed or after['id'] != before['id']:
                raise ValueError('Classic XML write cannot change unknown topic fields or ids safely')
            if after.get('class', 'topic') != 'topic':
                raise ValueError('Classic XML write cannot map unknown topic classes safely')
            if after.get('href') != before.get('href'):
                raise ValueError('Classic XML write cannot change hyperlinks safely')
            if after['title'] != before['title']:
                set_text(node, 'title', after['title'])
            if after.get('structureClass') != before.get('structureClass'):
                if after.get('structureClass'):
                    node.setAttribute('structure-class', after['structureClass'])
                else:
                    node.removeAttribute('structure-class')
            if set(after['notes']) - {'plain'} or set(after['notes']['plain']) - {'content'}:
                raise ValueError('Classic XML write supports plain notes only')
            if after['notes'] != before['notes']:
                notes = _one(node, 'notes')
                if notes is None:
                    notes = create(node, 'notes')
                    node.appendChild(notes)
                # Rich notes would otherwise take precedence over the updated plain text.
                if any(child.localName != 'plain' or child.namespaceURI != CONTENT_NAMESPACE
                       for child in _elements(notes)):
                    raise ValueError('Classic XML cannot replace rich notes safely')
                set_text(notes, 'plain', after['notes']['plain']['content'])
            for key, container, member, attribute in (
                    ('labels', 'labels', 'label', None),
                    ('markers', 'marker-refs', 'marker-ref', 'marker-id')):
                if after[key] == before[key]:
                    continue
                if key == 'markers' and any(set(marker) != {'markerId'} for marker in after[key]):
                    raise ValueError('Classic XML cannot write unknown marker fields safely')
                group = _one(node, container)
                if group is None:
                    group = create(node, container)
                    node.appendChild(group)
                existing = _elements(group, member)
                # Keep original attributes/unknown subelements for existing labels/markers.
                if len(after[key]) < len(before[key]) or after[key][:len(before[key])] != before[key]:
                    raise ValueError('Classic XML write can append labels/markers but cannot replace them safely')
                for value in after[key][len(existing):]:
                    item = create(group, member)
                    if attribute:
                        item.setAttribute(attribute, value['markerId'])
                    else:
                        item.appendChild(dom.createTextNode(value))
                    group.appendChild(item)
            old_groups, new_groups = before['children'], after['children']
            if set(old_groups) - set(new_groups):
                raise ValueError('Classic XML write cannot remove topic groups safely')
            children = _one(node, 'children')
            for kind, new_topics in new_groups.items():
                old_topics = old_groups.get(kind, [])
                if [item['id'] for item in new_topics[:len(old_topics)]] != [item['id'] for item in old_topics]:
                    raise ValueError('Classic XML write cannot remove, move, or reorder topics safely')
                if len(new_topics) < len(old_topics):
                    raise ValueError('Classic XML write cannot remove topics safely')
                group = None
                if children is not None:
                    group = next((item for item in _elements(children, 'topics')
                                  if item.getAttribute('type') == kind), None)
                nodes = _elements(group, 'topic') if group else []
                for index, original in enumerate(old_topics):
                    topic(nodes[index], original, new_topics[index])
                if len(new_topics) == len(old_topics):
                    continue
                if kind != 'attached':
                    raise ValueError('Classic XML write can only append attached topics safely')
                if children is None:
                    children = create(node, 'children')
                    node.appendChild(children)
                if group is None:
                    group = create(children, 'topics')
                    group.setAttribute('type', kind)
                    children.appendChild(group)
                for added in new_topics[len(old_topics):]:
                    child = create(group, 'topic')
                    child.setAttribute('id', added['id'])
                    group.appendChild(child)
                    empty = {'id': added['id'], 'title': '', 'children': {'attached': []},
                             'notes': {'plain': {'content': ''}}, 'labels': [], 'markers': []}
                    topic(child, empty, added)

        for node, before, after in zip(_elements(dom.documentElement, 'sheet'), old, sheets):
            if set(after) - {'id', 'title', 'class', 'rootTopic'}:
                raise ValueError('Classic XML write cannot change unknown sheet fields safely')
            if after.get('class', 'sheet') != 'sheet':
                raise ValueError('Classic XML write cannot map unknown sheet classes safely')
            if after['title'] != before['title']:
                set_text(node, 'title', after['title'])
            topic(_elements(node, 'topic')[0], before['rootTopic'], after['rootTopic'])
        output = dom.toxml(encoding='utf-8')
        # minidom serializes forbidden XML characters without rejecting them.
        # Validate the edited bytes before any destination can be replaced.
        _validate_xml(output, 'content.xml')
        return output
    finally:
        dom.unlink()


def write_xmind(path: str | Path, sheets: list[dict], document: XmindDocument | None = None) -> None:
    """Atomically write a rightward map, retaining unrelated original resources.

    For classic XML, existing sheet/topic ids and order are fixed. Plain titles
    and notes may change; labels, markers, and attached topics may be appended.
    Unsupported edits fail before the destination is changed.
    """
    normalized = _normalize_sheets(sheets)
    for sheet in normalized:
        sheet['rootTopic']['structureClass'] = RIGHT_STRUCTURE
    entries = dict(document.entries) if document else {}
    _check_entries(entries)
    removed = {name for name in entries if _thumbnail(name)}
    for name in removed:
        del entries[name]
    if document and document.format == 'xml':
        if 'content.xml' not in entries or 'content.json' in entries:
            raise ValueError('Classic Xmind document has inconsistent archive content')
        entries['content.xml'] = _classic_content(normalized, entries['content.xml'])
        manifest_name = 'META-INF/manifest.xml'
        if manifest_name in entries and removed:
            dom = _xml(entries[manifest_name], manifest_name)
            try:
                for node in list(dom.getElementsByTagName('*')):
                    for index in range(node.attributes.length):
                        attr = node.attributes.item(index)
                        if attr.localName == 'full-path' and attr.value in removed:
                            node.parentNode.removeChild(node)
                            break
                entries[manifest_name] = dom.toxml(encoding='utf-8')
            finally:
                dom.unlink()
    else:
        if document and document.format != 'json':
            raise ValueError('Unsupported Xmind document format')
        for sheet in normalized:
            sheet.setdefault('class', 'sheet')
            sheet['rootTopic'].setdefault('class', 'topic')
        entries['content.json'] = _encode_json(normalized)
        entries.setdefault('metadata.json', _encode_json({}))
        manifest = _json(entries['manifest.json'], 'manifest.json') if 'manifest.json' in entries else {}
        if not isinstance(manifest, dict) or not isinstance(manifest.get('file-entries', {}), dict):
            raise ValueError('Xmind manifest.json must contain an object file-entries')
        files = manifest.setdefault('file-entries', {})
        for name in removed:
            files.pop(name, None)
        for name in entries:
            if name != 'manifest.json':
                files.setdefault(name, {})
        entries['manifest.json'] = _encode_json(manifest)
    _check_entries(entries)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f'.{target.name}.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
            stream.flush()
            os.fsync(stream.fileno())
        if temporary.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError('Xmind archive exceeds the compressed size limit')
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

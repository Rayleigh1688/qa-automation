"""Real offline ZIP round trips and conservative classic-XML write boundaries."""
import copy
import io
import json
from pathlib import Path
import struct
import re
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from support import ROOT
from qa_core import xmind_archive as archive
from qa_core.xmind_archive import read_xmind, read_xmind_bytes, write_xmind, RIGHT_STRUCTURE


def sample():
    return [{'id': 'sheet-1', 'title': '测试用例', 'rootTopic': {
        'id': 'root-1', 'title': '需求', 'children': {'attached': [
            {'id': 'case-1', 'title': 'C01 登录', 'notes': {'plain': {'content': '已有备注'}},
             'labels': ['P0'], 'markers': [{'markerId': 'priority-1'}]}]}}}]


CLASSIC = b'''<?xml version="1.0" encoding="UTF-8"?>
<?keep processing-instruction?>
<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0"
 xmlns:ext="urn:qa:extension" xmlns:xlink="http://www.w3.org/1999/xlink" version="2.0">
 <sheet id="sheet-1" theme="theme-1"><title>Classic map</title>
  <topic id="root-1" structure-class="org.xmind.ui.map.clockwise" ext:original="yes">
   <title>Requirement</title><ext:title>Foreign extension</ext:title>
   <children><topics type="attached"><topic id="case-1" xlink:href="xap:attachments/proof.txt">
    <title>Case 01</title><notes><plain>Original note</plain></notes>
    <labels><label ext:style="kept">P0</label></labels>
    <marker-refs><marker-ref marker-id="priority-1" ext:unknown="kept"/></marker-refs>
    <ext:payload><ext:item value="retained"/></ext:payload>
   </topic></topics><topics type="detached"><topic id="float-1"><title>Floating</title></topic></topics></children>
  </topic><relationships><relationship id="rel-1" end1="case-1" end2="float-1"/></relationships>
 </sheet><!-- retain original comment -->
</xmap-content>'''


class XmindArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.source = self.folder / 'source.xmind'
        self.out = self.folder / 'out.xmind'

    def tearDown(self):
        self.temp.cleanup()

    def zip(self, entries, *, destination=None):
        with zipfile.ZipFile(destination or self.source, 'w', zipfile.ZIP_DEFLATED) as stream:
            for name, data in entries.items():
                stream.writestr(name, data)

    def modern(self, sheets=None, extras=None):
        entries = {'content.json': json.dumps(sheets or sample(), ensure_ascii=False).encode(),
                   'metadata.json': b'{"creator":{"name":"Original App"}}'}
        entries.update(extras or {})
        self.zip(entries)

    def classic(self, data=CLASSIC, extras=None):
        entries = {'content.xml': data, 'attachments/proof.txt': b'original attachment',
                   'styles.xml': b'<styles custom="keep"/>'}
        entries.update(extras or {})
        self.zip(entries)

    def test_new_modern_archive_round_trip_is_rightward_and_does_not_mutate_input(self):
        sheets = sample()
        before = copy.deepcopy(sheets)
        write_xmind(self.out, sheets)
        result = read_xmind(self.out)
        self.assertEqual(result.format, 'json')
        self.assertEqual(set(result.entries), {'content.json', 'metadata.json', 'manifest.json'})
        self.assertEqual(result.sheets[0]['rootTopic']['structureClass'], RIGHT_STRUCTURE)
        case = result.sheets[0]['rootTopic']['children']['attached'][0]
        self.assertEqual(case['notes']['plain']['content'], '已有备注')
        self.assertEqual(case['children']['attached'], [])
        self.assertEqual(sheets, before)
        self.assertEqual(json.loads(result.entries['manifest.json'])['file-entries'],
                         {'content.json': {}, 'metadata.json': {}})

    def test_bytes_reader_uses_the_same_snapshot_and_path_reader_limits_its_read(self):
        self.modern()
        data = self.source.read_bytes()
        self.assertEqual(read_xmind_bytes(data), read_xmind(self.source))
        with patch.object(archive, 'MAX_ARCHIVE_BYTES', len(data) - 1):
            with self.assertRaisesRegex(ValueError, 'compressed size'):
                read_xmind_bytes(data)
        with patch.object(archive, 'MAX_ARCHIVE_BYTES', 10):
            stream = io.BytesIO(data)
            with patch.object(Path, 'open', return_value=stream), patch.object(
                    archive, 'read_xmind_bytes', return_value='delegated') as parse:
                self.assertEqual(read_xmind(self.source), 'delegated')
            parse.assert_called_once_with(data[:11])

    def test_modern_round_trip_keeps_unknown_fields_attachments_and_secondary_sheets(self):
        sheets = sample()
        sheets[0]['theme'] = {'custom': {'font': 'NeverMind'}}
        case = sheets[0]['rootTopic']['children']['attached'][0]
        case.update({'href': 'xap:resources/proof.png', 'customMetadata': {'owner': 'human'},
                     'notes': {'plain': {'content': '已有备注'}, 'html': {'content': {'paragraphs': []}}}})
        sheets.append({'id': 'sheet-2', 'title': '附件', 'rootTopic': {'id': 'root-2', 'title': '资料'}})
        extras = {'resources/proof.png': b'\x89PNG\r\nfixture', 'resources/': b'',
                  'META-INF/custom.json': b'keep exact bytes', 'content.xml': b'compatibility warning'}
        self.modern(sheets, extras)
        original_bytes = self.source.read_bytes()
        document = read_xmind(self.source)
        updated = copy.deepcopy(document.sheets)
        updated[0]['rootTopic']['children']['attached'][0]['title'] += ' [通过]'
        write_xmind(self.out, updated, document)
        result = read_xmind(self.out)
        for name, data in extras.items():
            self.assertEqual(result.entries[name], data)
        self.assertEqual(result.entries['metadata.json'], document.entries['metadata.json'])
        self.assertEqual(result.sheets[0]['theme'], sheets[0]['theme'])
        self.assertEqual(result.sheets[0]['rootTopic']['children']['attached'][0]['customMetadata'], {'owner': 'human'})
        self.assertEqual(result.sheets[1]['title'], '附件')
        self.assertEqual(self.source.read_bytes(), original_bytes)

    def test_stale_thumbnails_removed_from_json_manifest_but_other_entries_kept(self):
        manifest = {'custom': 'keep', 'file-entries': {'content.json': {'media-type': 'application/json'},
                    'Thumbnails/thumbnail.png': {}, 'thumbnail.jpg': {}, 'resources/proof.png': {'custom': 1},
                    'resources/thumbnail.png': {'media-type': 'image/png'}}}
        self.modern(extras={'manifest.json': json.dumps(manifest).encode(), 'Thumbnails/thumbnail.png': b'old',
                            'thumbnail.jpg': b'old', 'resources/proof.png': b'image',
                            'resources/thumbnail.png': b'human attachment'})
        document = read_xmind(self.source)
        write_xmind(self.out, document.sheets, document)
        result = read_xmind(self.out)
        self.assertNotIn('Thumbnails/thumbnail.png', result.entries)
        self.assertNotIn('thumbnail.jpg', result.entries)
        written = json.loads(result.entries['manifest.json'])
        self.assertEqual(written['custom'], 'keep')
        self.assertNotIn('Thumbnails/thumbnail.png', written['file-entries'])
        self.assertEqual(written['file-entries']['resources/proof.png'], {'custom': 1})
        self.assertEqual(result.entries['resources/thumbnail.png'], b'human attachment')
        self.assertEqual(written['file-entries']['resources/thumbnail.png'], {'media-type': 'image/png'})

    def test_classic_xml_read_and_round_trip_preserves_unknown_xml_and_attachments(self):
        self.classic()
        document = read_xmind(self.source)
        self.assertEqual(document.format, 'xml')
        case = document.sheets[0]['rootTopic']['children']['attached'][0]
        self.assertEqual(case['href'], 'xap:attachments/proof.txt')
        self.assertEqual(case['labels'], ['P0'])
        updated = copy.deepcopy(document.sheets)
        case = updated[0]['rootTopic']['children']['attached'][0]
        case['title'] += ' [PASS]'
        case['notes']['plain']['content'] += '\nactual evidence'
        case['labels'].append('通过')
        case['markers'].append({'markerId': 'task-done'})
        case['children']['attached'].append({'id': 'result-1', 'title': '执行结果',
                                            'notes': {'plain': {'content': 'offline fixture only'}}})
        write_xmind(self.out, updated, document)
        result = read_xmind(self.out)
        self.assertEqual(result.format, 'xml')
        self.assertNotIn('content.json', result.entries)
        self.assertEqual(result.entries['attachments/proof.txt'], b'original attachment')
        self.assertEqual(result.entries['styles.xml'], document.entries['styles.xml'])
        xml = result.entries['content.xml'].decode()
        for expected in ('ext:original="yes"', 'Foreign extension', 'ext:style="kept"',
                         'ext:unknown="kept"', 'ext:payload', 'retain original comment',
                         'keep processing-instruction', 'end1="case-1"'):
            self.assertIn(expected, xml)
        after = result.sheets[0]['rootTopic']['children']['attached'][0]
        self.assertEqual(after['labels'], ['P0', '通过'])
        self.assertEqual(after['children']['attached'][0]['id'], 'result-1')
        self.assertIn('actual evidence', after['notes']['plain']['content'])
        self.assertEqual(result.sheets[0]['rootTopic']['structureClass'], RIGHT_STRUCTURE)

    def test_classic_thumbnail_manifest_pruning_preserves_other_manifest_entries(self):
        manifest = b'''<manifest xmlns="urn:xmind:xmap:xmlns:manifest:1.0"><file-entry full-path="Thumbnails/thumbnail.png"/>
            <file-entry full-path="attachments/proof.txt" custom="keep"/></manifest>'''
        self.classic(extras={'META-INF/manifest.xml': manifest, 'Thumbnails/thumbnail.png': b'old'})
        document = read_xmind(self.source)
        write_xmind(self.out, document.sheets, document)
        result = read_xmind(self.out)
        self.assertNotIn('Thumbnails/thumbnail.png', result.entries)
        self.assertNotIn(b'Thumbnails/thumbnail.png', result.entries['META-INF/manifest.xml'])
        self.assertIn(b'custom="keep"', result.entries['META-INF/manifest.xml'])

    def test_classic_repeated_result_update_keeps_topic_ids_and_unknown_xml(self):
        self.classic()
        document = read_xmind(self.source)
        updated = copy.deepcopy(document.sheets)
        case = updated[0]['rootTopic']['children']['attached'][0]
        case['children']['attached'].append({'id': 'result-1', 'class': 'topic', 'title': 'Results',
            'children': {'attached': [{'id': 'status-1', 'class': 'topic', 'title': 'FAIL'}]}})
        write_xmind(self.out, updated, document)
        first = read_xmind(self.out)
        next_sheets = copy.deepcopy(first.sheets)
        next_sheets[0]['class'] = 'sheet'
        leaf = next_sheets[0]['rootTopic']['children']['attached'][0]['children']['attached'][0]['children']['attached'][0]
        leaf['title'] = 'PASS'
        write_xmind(self.folder / 'second.xmind', next_sheets, first)
        second = read_xmind(self.folder / 'second.xmind')
        written = second.sheets[0]['rootTopic']['children']['attached'][0]['children']['attached'][0]
        self.assertEqual(written['id'], 'result-1')
        self.assertEqual(written['children']['attached'][0]['title'], 'PASS')
        self.assertIn(b'ext:payload', second.entries['content.xml'])
        self.assertEqual(second.entries['attachments/proof.txt'], first.entries['attachments/proof.txt'])

    def test_classic_namespace_prefix_is_preserved_for_new_topics(self):
        data = CLASSIC.replace(b'xmlns="urn:xmind:xmap:xmlns:content:2.0"',
                               b'xmlns:m="urn:xmind:xmap:xmlns:content:2.0"')
        names = b'xmap-content|sheet|topic|title|children|topics|notes|plain|labels|label|marker-refs|marker-ref|relationships|relationship'
        data = re.sub(b'(<\\/?)(?:' + names + b')(?=[\\s>/])',
                      lambda match: match.group(0).replace(match.group(1), match.group(1) + b'm:', 1), data)
        self.classic(data)
        document = read_xmind(self.source)
        document.sheets[0]['rootTopic']['children']['attached'].append({'id': 'new-1', 'title': 'New case'})
        write_xmind(self.out, document.sheets, document)
        result = read_xmind(self.out)
        self.assertEqual(result.sheets[0]['rootTopic']['children']['attached'][-1]['title'], 'New case')
        self.assertIn(b'<m:topic id="new-1">', result.entries['content.xml'])

    def test_classic_unsupported_edits_fail_without_touching_destination(self):
        self.classic()
        document = read_xmind(self.source)
        self.out.write_bytes(b'untouched destination')
        changes = [lambda s: s[0].update({'theme': {'new': True}}),
                   lambda s: s[0]['rootTopic']['children']['attached'].clear(),
                   lambda s: s[0]['rootTopic']['children']['attached'][0].update({'href': 'https://example.com'}),
                   lambda s: s[0]['rootTopic']['children']['attached'][0].update({'labels': ['FAIL']})]
        for change in changes:
            with self.subTest(change=change):
                updated = copy.deepcopy(document.sheets)
                change(updated)
                with self.assertRaises(ValueError):
                    write_xmind(self.out, updated, document)
                self.assertEqual(self.out.read_bytes(), b'untouched destination')

    def test_classic_rich_notes_survive_untouched_but_refuse_conflicting_plain_update(self):
        self.classic(CLASSIC.replace(b'<plain>Original note</plain>',
                                    b'<plain>Original note</plain><html><p xmlns="http://www.w3.org/1999/xhtml">Rich</p></html>'))
        document = read_xmind(self.source)
        write_xmind(self.out, document.sheets, document)
        self.assertIn(b'Rich', read_xmind(self.out).entries['content.xml'])
        document.sheets[0]['rootTopic']['children']['attached'][0]['notes']['plain']['content'] = 'updated'
        with self.assertRaisesRegex(ValueError, 'rich notes'):
            write_xmind(self.out, document.sheets, document)

    def test_classic_illegal_xml_characters_cannot_replace_destination(self):
        self.classic()
        original = self.source.read_bytes()
        document = read_xmind(self.source)
        self.out.write_bytes(b'original destination')
        changes = [lambda topic: topic.update({'title': 'bad\x00title'}),
                   lambda topic: topic['notes']['plain'].update({'content': '\x1b[31mactual output'}),
                   lambda topic: topic['children']['attached'].append({'id': 'new\x0b', 'title': 'Result'}),
                   lambda topic: topic['markers'].append({'markerId': 'bad\x00marker'}),
                   lambda topic: topic.update({'title': 'bad\ud800title'})]
        for change in changes:
            with self.subTest(change=change):
                sheets = copy.deepcopy(document.sheets)
                change(sheets[0]['rootTopic']['children']['attached'][0])
                with self.assertRaisesRegex(ValueError, 'invalid XML'):
                    write_xmind(self.out, sheets, document)
                self.assertEqual(self.out.read_bytes(), b'original destination')
                self.assertEqual(self.source.read_bytes(), original)
                self.assertEqual(set(self.folder.iterdir()), {self.source, self.out})

    def test_rejects_duplicate_zip_names_and_encrypted_archives(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.source, 'w') as stream:
                stream.writestr('content.json', '[]')
                stream.writestr('content.json', '[]')
        with self.assertRaisesRegex(ValueError, 'duplicate entry'):
            read_xmind(self.source)
        self.modern()
        data = bytearray(self.source.read_bytes())
        struct.pack_into('<H', data, 6, struct.unpack_from('<H', data, 6)[0] | 1)
        central = data.index(b'PK\x01\x02')
        struct.pack_into('<H', data, central + 8, struct.unpack_from('<H', data, central + 8)[0] | 1)
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'Encrypted'):
            read_xmind(self.source)

    def test_rejects_archive_size_entry_count_and_uncompressed_size_limits(self):
        self.modern(extras={'resources/a': b'a' * 20, 'resources/b': b'b' * 20})
        for setting, limit, message in [('MAX_ARCHIVE_BYTES', 1, 'compressed size'),
                                       ('MAX_ENTRY_BYTES', 10, 'entry exceeds'),
                                       ('MAX_TOTAL_BYTES', 30, 'uncompressed size'),
                                       ('MAX_ENTRIES', 1, 'too many')]:
            with self.subTest(setting=setting), patch.object(archive, setting, limit):
                with self.assertRaisesRegex(ValueError, message):
                    read_xmind(self.source)

    def test_rejects_unsafe_archive_paths_without_extracting_anything(self):
        for name in ('../outside', '/absolute', 'C:/absolute', 'resources\\outside'):
            with self.subTest(name=name):
                self.zip({'content.json': json.dumps(sample()).encode(), name: b'never extracted'})
                with self.assertRaisesRegex(ValueError, 'unsafe entry'):
                    read_xmind(self.source)
        self.assertEqual(list(self.folder.iterdir()), [self.source])

    def test_rejects_xml_entities_in_utf8_and_utf16(self):
        xml = '<!DOCTYPE xmap-content [<!ENTITY secret SYSTEM "file:///etc/passwd">]><xmap-content>&secret;</xmap-content>'
        for encoding in ('utf-8', 'utf-16'):
            with self.subTest(encoding=encoding):
                self.classic(xml.encode(encoding))
                with self.assertRaisesRegex(ValueError, 'entities'):
                    read_xmind(self.source)

    def test_rejects_arbitrary_xml_node_depth_and_wrong_namespace(self):
        self.classic()
        with patch.object(archive, 'MAX_XML_NODES', 2):
            with self.assertRaisesRegex(ValueError, 'node count'):
                read_xmind(self.source)
        self.classic(CLASSIC.replace(b'urn:xmind:xmap:xmlns:content:2.0', b'urn:unknown'))
        with self.assertRaisesRegex(ValueError, 'namespace'):
            read_xmind(self.source)

    def test_xml_node_limit_covers_comments_pi_cdata_text_and_attributes_before_dom(self):
        xml = (f'<xmap-content xmlns="{archive.CONTENT_NAMESPACE}"><sheet id="s">'
               '<topic id="r"/></sheet></xmap-content>').encode()
        extras = [b'<!--x-->' * 30, b'<?keep x?>' * 30,
                  b'<![CDATA[x]]>' * 30, b'x<!--x-->' * 30]
        documents = [xml.replace(b'</xmap-content>', extra + b'</xmap-content>') for extra in extras]
        attributes = b' '.join(f'a{i}="x"'.encode() for i in range(30))
        documents.append(xml.replace(b'<topic id="r"', b'<topic id="r" ' + attributes))
        for data in documents:
            with self.subTest(data=data):
                self.classic(data)
                with patch.object(archive, 'MAX_XML_NODES', 20), patch.object(
                        archive.minidom, 'parseString') as build_dom:
                    with self.assertRaisesRegex(ValueError, 'node count'):
                        read_xmind(self.source)
                    build_dom.assert_not_called()

    def test_rejects_missing_content_invalid_json_and_invalid_topic_shape(self):
        cases = [{'resources/file': b'no content'}, {'content.json': b'not JSON'},
                 {'content.json': b'[]'}, {'content.json': b'{"sheets":[]}'},
                 {'content.json': b'[{"id":"s","rootTopic":{"id":"r","children":[]}}]'},
                 {'content.xml': b'<xmap-content>'}, {'content.json': b'[{"id":"s","id":"s2"}]'}]
        for entries in cases:
            with self.subTest(entries=entries):
                self.zip(entries)
                with self.assertRaises(ValueError):
                    read_xmind(self.source)
        self.source.write_bytes(b'not a zip')
        with self.assertRaisesRegex(ValueError, 'ZIP'):
            read_xmind(self.source)

    def test_duplicate_topic_ids_depth_and_count_are_rejected(self):
        sheets = sample()
        sheets[0]['rootTopic']['children']['attached'][0]['id'] = 'root-1'
        self.modern(sheets)
        with self.assertRaisesRegex(ValueError, 'duplicate id'):
            read_xmind(self.source)
        self.modern()
        with patch.object(archive, 'MAX_TOPICS', 1):
            with self.assertRaisesRegex(ValueError, 'topic count'):
                read_xmind(self.source)
        with patch.object(archive, 'MAX_DEPTH', 0):
            with self.assertRaisesRegex(ValueError, 'topic depth'):
                read_xmind(self.source)

    def test_atomic_write_failure_preserves_existing_destination_and_removes_temp(self):
        self.out.write_bytes(b'original destination')
        with patch.object(archive.os, 'replace', side_effect=OSError('simulated failure')):
            with self.assertRaisesRegex(OSError, 'simulated failure'):
                write_xmind(self.out, sample())
        self.assertEqual(self.out.read_bytes(), b'original destination')
        self.assertEqual(list(self.folder.iterdir()), [self.out])

    def test_invalid_writer_input_and_manifest_cannot_overwrite_destination(self):
        self.out.write_bytes(b'original destination')
        with self.assertRaises(ValueError):
            write_xmind(self.out, [])
        self.modern(extras={'manifest.json': b'[]'})
        document = read_xmind(self.source)
        with self.assertRaisesRegex(ValueError, 'manifest'):
            write_xmind(self.out, document.sheets, document)
        self.assertEqual(self.out.read_bytes(), b'original destination')


if __name__ == '__main__':
    unittest.main()

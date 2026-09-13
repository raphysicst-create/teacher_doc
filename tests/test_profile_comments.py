"""Regression for legal XML nodes found by the isolated registration run."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.claude/skills/hwpx/scripts'))
from page_guard import _xml_structure_hash


class ProfileXmlTests(unittest.TestCase):
    def test_comments_and_processing_instructions_are_preserved(self):
        original = b'<root><!-- preserve --><?sample value?><cell width="100"/></root>'
        digest = _xml_structure_hash(original)
        self.assertEqual(digest, _xml_structure_hash(original))
        for replacement in (original.replace(b'preserve', b'changed'), original.replace(b'100', b'200'),
                            original.replace(b'value', b'new')):
            self.assertNotEqual(digest, _xml_structure_hash(replacement))

    def test_visible_text_can_change_without_ignoring_layout(self):
        original = b'<root xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"><!--note--><hp:run charPrIDRef="10"><hp:t>old</hp:t></hp:run></root>'
        self.assertEqual(_xml_structure_hash(original), _xml_structure_hash(original.replace(b'old', b'new')))
        self.assertNotEqual(_xml_structure_hash(original), _xml_structure_hash(original.replace(b'"10"', b'"11"')))


if __name__ == '__main__':
    unittest.main()

import logging
import os
import time
from unittest import (
    TestCase,
)
from unittest.mock import patch, call

import xml_serial


class TestXMLSerialFunctions(TestCase):

    def test_get_sorted_list_and_repeated_items(self):
        result = xml_serial.get_sorted_list_and_repeated_items(
            list("Abacates")
        )
        self.assertEqual(
            result, (("A", "a", "b", "c", "e", "s", "t"), (("a", 2),)))

    def test_get_sorted_list_and_repeated_items_no_repeated_items(self):
        result = xml_serial.get_sorted_list_and_repeated_items(list("AZY"))
        self.assertEqual(result, (("A", "Y", "Z"), tuple(tuple())))


class TestAOPChecker(TestCase):
    def setUp(self):
        self.aop_checker = xml_serial.AOPChecker(
            'proc/acron/ahead', 'xml/acron/ahead'
        )

    def test__find_repeatitions_returns_error(self):
        self.assertEqual(
            self.aop_checker._find_repeatitions(["c", "b", "a", "b", ]),
            {"error_msg": 'Em proc/acron/ahead b ocorre 2 vezes'}
        )

    def test__find_repeatitions_returns_empty_dict(self):
        self.assertEqual(
            self.aop_checker._find_repeatitions(["c", "a", "b", ]), {}
        )

    def test__compare_returns_empty_dict(self):
        self.assertEqual(
            self.aop_checker._compare(["c", "a", "b", ], ["c", "a", "b", ]), {}
        )

    def test__compare_returns_mx_append(self):
        self.assertEqual(
            self.aop_checker._compare(["c", "a", "b", ], ["x", "y"]),
            {"mx_append":
             "mx xml/acron/ahead from=2 append=proc/acron/ahead -all now"}
        )

    @patch("xml_serial.get_documents")
    def test_check_db_status_returns_error(self, mock_get_docs):
        mock_get_docs.return_value = ["c", "b", "a", "b", ]
        result = self.aop_checker.check_db_status()
        self.assertEqual(
            result, {"error_msg": 'Em proc/acron/ahead b ocorre 2 vezes'})


class TestXMLSerial(TestCase):
    def setUp(self):
        self.SRC_FILES = (
            "fixtures/xmlserial/title/title.mst",
            "fixtures/xmlserial/title/title.xrf",
            "fixtures/xmlserial/issue/issue.mst",
            "fixtures/xmlserial/issue/issue.xrf",
        )
        self.DEST_FILES = (
            "fixtures/proc/title/title.mst",
            "fixtures/proc/title/title.xrf",
            "fixtures/proc/issue/issue.mst",
            "fixtures/proc/issue/issue.xrf",
        )
        config = {
            "XML_SERIAL_LOCATION": "fixtures/xmlserial",
        }
        self.xmlserial = xml_serial.XMLSerial(config, "fixtures/proc")

    def tearDown(self):
        for f in self.DEST_FILES + self.SRC_FILES:
            if os.path.isfile(f):
                os.unlink(f)

    def create_file(self, filename, content=''):
        path = os.path.dirname(filename)
        if path and not os.path.isdir(path):
            os.makedirs(path)
        with open(filename, "w") as fp:
            fp.write(content)

    def test_make_title_and_issue_updated_create_files(self):
        for f in self.SRC_FILES:
            self.create_file(f)
        self.xmlserial.make_title_and_issue_updated()
        for f in self.DEST_FILES:
            self.assertTrue(os.path.isfile(f))

    def test_make_title_and_issue_updated_updates_dest_with_source(self):
        for f in self.DEST_FILES:
            self.create_file(f, "DEST")
        for f in self.SRC_FILES:
            self.create_file(f, "SOURCE")
        self.xmlserial.make_title_and_issue_updated()
        for f in self.DEST_FILES:
            with open(f) as fp:
                c = fp.read()
                self.assertEqual(c, "SOURCE")

    def test_make_title_and_issue_updated_does_not_update(self):
        for f in self.SRC_FILES:
            self.create_file(f, "SOURCE")
        time.sleep(1)
        for f in self.DEST_FILES:
            self.create_file(f, "DEST")
        self.xmlserial.make_title_and_issue_updated()
        for f in self.DEST_FILES:
            with open(f) as fp:
                c = fp.read()
                self.assertEqual(c, "DEST")

    @patch("xml_serial.XMLSerial.exists")
    def test__check_db_status_returns_error_not_found(self, mock_exists):
        mock_exists.return_value = False
        result = self.xmlserial._check_db_status("acron", "volnum")
        self.assertEqual(
            result,
            {"error_msg":
             'Not found fixtures/xmlserial/acron/volnum/base/volnum.mst'})

    @patch("xml_serial.XMLSerial.exists")
    def test__check_db_status_returns_items_to_copy(self, mock_exists):
        mock_exists.return_value = True
        result = self.xmlserial._check_db_status("acron", "volnum")
        self.assertEqual(
            result, {
                "files_info": [
                    ('fixtures/proc/acron/volnum/base/volnum.mst', (0, 0)),
                    ('fixtures/proc/acron/volnum/base/volnum.xrf', (0, 0))],
                "items_to_copy": (
                    'fixtures/xmlserial/acron/volnum/base/volnum',
                    'fixtures/proc/acron/volnum/base/volnum')
            }
        )

    @patch("xml_serial.XMLSerial.exists")
    def test__check_db_status_returns_items_to_copy_for_aop(self, mock_exists):
        mock_exists.return_value = True
        result = self.xmlserial._check_db_status("acron", "2019nahead")
        self.assertEqual(
            result, {
                "files_info": [
                    ('fixtures/proc/acron/2019nahead/base/2019nahead.mst', (0, 0)),
                    ('fixtures/proc/acron/2019nahead/base/2019nahead.xrf', (0, 0))],
                "items_to_copy": (
                    'fixtures/xmlserial/acron/2019nahead/base/2019nahead',
                    'fixtures/proc/acron/2019nahead/base/2019nahead')
            }
        )

    @patch("xml_serial.XMLSerial.synchronize")
    def test__copy_to_proc_serial_calls_synchronize(self, mock_synchronize):
        self.xmlserial._copy_to_proc_serial(
            'fixtures/xmlserial/acron/volnum/base/volnum',
            'fixtures/proc/acron/volnum/base/volnum'
            )
        self.assertEqual(
            mock_synchronize.call_args_list,
            [
                call('fixtures/xmlserial/acron/volnum/base/volnum.mst',
                     'fixtures/proc/acron/volnum/base/volnum.mst'),
                call('fixtures/xmlserial/acron/volnum/base/volnum.xrf',
                     'fixtures/proc/acron/volnum/base/volnum.xrf'),

            ]
        )

    @patch("xml_serial.os_system")
    def test_update_proc_serial_calls_os_system(self, mock_os_system):
        data = [
            {"mx_append":
             "mx xml/acron/ahead from=2 append=proc/acron/ahead -all now"}
        ]
        self.xmlserial.update_proc_serial(data, logging)
        mock_os_system.assert_called_once_with(
            "mx xml/acron/ahead from=2 append=proc/acron/ahead -all now")

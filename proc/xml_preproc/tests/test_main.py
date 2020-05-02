import logging
import os
import time
from unittest import (
    TestCase,
)
from unittest.mock import patch, call

from scilistatest_and_coletaxml import (
    sort_scilista,
    check_scilista_items_are_registered,
    find_conflicting_items,
    items_to_retry_updating,
)


class TestMain(TestCase):

    def test_sort_scilista(self):
        scilista = [
            "rabc v1n1",
            "rabc v1n10",
            "gabc v1n11 del",
            "dabc v1n1pr",
            "fabc v1n2pr del",
            "gabc 2010nahead",
            "xabc 2000naheadpr",
            "babc 2011nahead del",
            "rabc 2009naheadpr del",
            "abc v1n1",
            "abc v1n10",
            "abc v1n11 del",
            "abc v1n1pr",
            "abc v1n2pr del",
            "abc 2010nahead",
            "abc 2000naheadpr",
            "abc 2011nahead del",
            "abc 2009naheadpr del",
        ]
        expected = [
            "abc 2009naheadpr del",
            "abc 2011nahead del",
            "abc v1n11 del",
            "abc v1n2pr del",
            "babc 2011nahead del",
            "fabc v1n2pr del",
            "gabc v1n11 del",
            "rabc 2009naheadpr del",
            "abc 2000naheadpr",
            "abc v1n1pr",
            "dabc v1n1pr",
            "xabc 2000naheadpr",
            "abc 2010nahead",
            "gabc 2010nahead",
            "abc v1n1",
            "abc v1n10",
            "rabc v1n1",
            "rabc v1n10",
        ]
        result = sort_scilista(scilista)
        self.assertEqual(result, expected)

    @patch("scilistatest_and_coletaxml.logger.error")
    def test_find_conflicting_items(self, mock_logger):
        scilista_items = [
            "abc 2009naheadpr del",
            "abc 2009naheadpr",
        ]
        find_conflicting_items(scilista_items)
        mock_logger.assert_called_once_with((
            "Encontrados "
            "'abc 2009naheadpr' e 'abc 2009naheadpr del' na scilistaxml. "
            "Mantenha 'abc 2009naheadpr' se deve ser atualizado. "
            "Mantenha 'abc 2009naheadpr del' se deve ser apagado."
            )
        )

    def test_check_scilista_items_are_registered_returns_all(self):
        registered_issues = [
            "abc 2009naheadpr",
            "abc 2011nahead",
            "abc v1n11",
        ]
        scilista_items = [
            "abc 2009naheadpr del",
            "abc 2011nahead del",
            "abc v1n11 del",
        ]
        expected = [
            ("abc", "v1n11"),
            ("abc", "2009naheadpr"),
            ("abc", "2011nahead"),
        ]
        result = check_scilista_items_are_registered(
            scilista_items, registered_issues)
        self.assertEqual(set(result), set(expected))

    def test_check_scilista_items_are_registered_returns_registered_items(
            self):
        registered_issues = [
            "abc v1n11",
        ]
        scilista_items = [
            "abc 2009naheadpr del",
            "abc 2011nahead del",
            "abc v1n11 del",
        ]
        expected = [
            ("abc", "v1n11"),
        ]
        result = check_scilista_items_are_registered(
            scilista_items, registered_issues)
        self.assertEqual(result, expected)

    @patch("scilistatest_and_coletaxml.logger.error")
    def test_check_scilista_items_are_registered_log_errors(
            self, mock_logger):
        registered_issues = [
            "abc v1n11",
        ]
        scilista_items = [
            "abc 2009naheadpr del",
            "abc 2011nahead del",
            "abc v1n11 del",
        ]
        check_scilista_items_are_registered(
            scilista_items, registered_issues)
        self.assertEqual(
            mock_logger.call_args_list,
            [
                call('Linha 1: "abc 2009naheadpr" nao esta registrado'),
                call('Linha 2: "abc 2011nahead" nao esta registrado')
            ]
        )

    def test_check_scilista_items_are_registered_does_not_return_repeatition(
            self):
        registered_issues = [
            "abc v1n11",
        ]
        scilista_items = [
            "abc 2009naheadpr del",
            "abc 2011nahead del",
            "abc v1n11 del",
            "abc v1n11",
        ]
        result = check_scilista_items_are_registered(
            scilista_items, registered_issues)
        self.assertEqual(result, [("abc", "v1n11")])

    @patch("scilistatest_and_coletaxml.fileinfo")
    def test_items_to_retry_updating(self, mock_fileinfo):
        mock_fileinfo.side_effect = [
            (0, 0),
        ]
        items = [
            {"files_info": [
                    ['', (0, 0)],
                    ['', (0, 0)],
                ]
             }
        ]
        result = items_to_retry_updating(items)
        self.assertEqual(result, items)


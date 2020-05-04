import os
from unittest import (
    TestCase,
)
from unittest.mock import patch, call, Mock

from scilistatest_and_coletaxml import (
    sort_scilista,
    check_scilista_items_are_registered,
    items_to_retry_updating,
    _scilista_info,
    scilista_info,
    main,
    ERROR_FILE,
    SciListaXML,
)


class TestSciListaXML(TestCase):

    @patch("scilistatest_and_coletaxml.logger.error")
    def test_find_conflicting_items(self, mock_logger):
        scilista_items = [
            "abc 2009naheadpr del",
            "abc 2009naheadpr",
        ]
        scilistaxml = SciListaXML(scilista_items, Mock())
        scilistaxml._find_conflicting_items()
        mock_logger.assert_called_once_with((
            "Encontrados "
            "'abc 2009naheadpr' e 'abc 2009naheadpr del' na scilistaxml. "
            "Mantenha 'abc 2009naheadpr' para atualizar. "
            "Mantenha 'abc 2009naheadpr del' para nao ser publicado."
            )
        )


class TestMainBase(TestCase):
    pass


class TestMainFunctions(TestMainBase):

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
    def test_items_to_retry_updating_returns_items(self, mock_fileinfo):
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

    @patch("scilistatest_and_coletaxml.fileinfo")
    def test_items_to_retry_updating_returns_empty_list(self, mock_fileinfo):
        mock_fileinfo.side_effect = [
            (1, 1),
            (1, 1),
        ]
        items = [
            {"files_info": [
                    ['', (0, 0)],
                    ['', (0, 0)],
                ]
             }
        ]
        result = items_to_retry_updating(items)
        self.assertEqual(result, [])

    @patch("scilistatest_and_coletaxml.fileinfo")
    def test_items_to_retry_updating_returns_same_items_because_one_file_was_not_updated(self, mock_fileinfo):
        mock_fileinfo.side_effect = [
            (1, 1),
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

    def test__scilista_info(self):
        scilista_items = [
            "rabc v1n1",
            "rabc v1n10",
            "gabc v1n11 del",
            "dabc v1n1pr",
        ]
        expected = [
            "",
            "scilistaxml.lst original (4 itens)",
            "==================================",
            "",
            "rabc v1n1",
            "rabc v1n10",
            "gabc v1n11 del",
            "dabc v1n1pr",
            "",
        ]

        result = _scilista_info(
            "scilistaxml.lst original (4 itens)", scilista_items)
        self.assertEqual(result, "\n".join(expected))

    def test_scilista_info(self):
        scilista_items = [
            "rabc v1n1",
            "rabc v1n10",
            "gabc v1n11 del",
            "dabc v1n1pr",
            "rabc v1n1",
        ]
        expected = [
            "",
            "scilistaxml.lst original (5 itens)",
            "==================================",
            "",
            "rabc v1n1",
            "rabc v1n10",
            "gabc v1n11 del",
            "dabc v1n1pr",
            "rabc v1n1",
            "",
            "",
            "scilistaxml.lst ordenada (5 itens)",
            "==================================",
            "",
            "dabc v1n1pr",
            "gabc v1n11 del",
            "rabc v1n1",
            "rabc v1n1",
            "rabc v1n10",
            "",
        ]

        result = scilista_info(
            "scilistaxml.lst", scilista_items)
        self.assertEqual(result, "\n".join(expected))


class TestMainMailx(TestMainBase):

    @patch("scilistatest_and_coletaxml.os_system")
    @patch("scilistatest_and_coletaxml.XMLSerial.make_title_and_issue_updated")
    @patch("scilistatest_and_coletaxml.config_filepath")
    def test_os_system_called_with_errors(
            self, mock_config_filepath, mock_update,
            mock_os_system):
        mock_config_filepath.return_value = (
            'xml_preproc/xmlpreproc_config.ini.template')
        main()
        cmd = ('mailx marca@example.com -b "sysadm@example.com" '
               '-c "infras@example.com, prod@example.com" '
               '-s "[XML PREPROC][SciELO TESTE][] Erros encontrados" '
               '< xmlpreproc_outs_msg_email.txt')
        mock_os_system.assert_called_once_with(cmd)


class TestMainSendEmail(TestMainBase):

    @patch("scilistatest_and_coletaxml.send_mail")
    @patch("scilistatest_and_coletaxml.XMLSerial.make_title_and_issue_updated")
    @patch("scilistatest_and_coletaxml.config_filepath")
    def test_send_email_with_errors_because_scilista_is_not_found(
            self, mock_config_filepath, mock_update, mock_send_mail):
        mock_config_filepath.return_value = (
            'xml_preproc/xmlpreproc_config.ini.template')
        main()
        mock_send_mail.assert_called_once_with(
            "SciELO TESTE",
            "marca@example.com", "sysadm@example.com",
            "infras@example.com, prod@example.com",
            "Erros encontrados",
            '',
            "xmlpreproc_outs_msg_email.txt"
        )

    @patch("scilistatest_and_coletaxml.get_registered_issues")
    @patch("scilistatest_and_coletaxml.file_readlines")
    @patch("scilistatest_and_coletaxml.send_mail")
    @patch("scilistatest_and_coletaxml.XMLSerial.make_title_and_issue_updated")
    @patch("scilistatest_and_coletaxml.config_filepath")
    def test_main_send_email_with_errors_because_no_issue_is_registered(
            self,
            mock_config_filepath,
            mock_update,
            mock_send_mail,
            mock_readlines,
            mock_get_registered_issues):
        mock_readlines.side_effect = [
            [],
            ["abc v1n1"],
        ]
        mock_config_filepath.return_value = (
            'xml_preproc/xmlpreproc_config.ini.template')
        mock_get_registered_issues.return_value = []
        main()
        mock_send_mail.assert_called_once_with(
            "SciELO TESTE",
            "marca@example.com", "sysadm@example.com",
            "infras@example.com, prod@example.com",
            "Erros encontrados",
            '',
            "xmlpreproc_outs_msg_email.txt"
        )

    @patch("scilistatest_and_coletaxml.get_registered_issues")
    @patch("scilistatest_and_coletaxml.file_readlines")
    @patch("scilistatest_and_coletaxml.send_mail")
    @patch("scilistatest_and_coletaxml.XMLSerial.make_title_and_issue_updated")
    @patch("scilistatest_and_coletaxml.config_filepath")
    def test_main_send_email_with_errors_because_scilista_has_repeatition(
            self,
            mock_config_filepath,
            mock_update,
            mock_send_mail,
            mock_readlines,
            mock_get_registered_issues):
        mock_readlines.side_effect = [
            [],
            ["abc v1n1",
             "abc v1n1"],
        ]
        mock_config_filepath.return_value = (
            'xml_preproc/xmlpreproc_config.ini.template')
        mock_get_registered_issues.return_value = [
            "abc v1n1"
        ]
        main()
        mock_send_mail.assert_called_once_with(
            "SciELO TESTE",
            "marca@example.com", "sysadm@example.com",
            "infras@example.com, prod@example.com",
            "Erros encontrados",
            '',
            "xmlpreproc_outs_msg_email.txt"
        )

    @patch("scilistatest_and_coletaxml.get_registered_issues")
    @patch("scilistatest_and_coletaxml.file_readlines")
    @patch("scilistatest_and_coletaxml.send_mail")
    @patch("scilistatest_and_coletaxml.XMLSerial.make_title_and_issue_updated")
    @patch("scilistatest_and_coletaxml.config_filepath")
    def test_main_send_email_with_errors_because_scilista_there_are_conflicts(
            self,
            mock_config_filepath,
            mock_update,
            mock_send_mail,
            mock_readlines,
            mock_get_registered_issues):
        mock_readlines.side_effect = [
            [],
            ["abc v1n1",
             "abc v1n1 del"
             ],
        ]
        mock_config_filepath.return_value = (
            'xml_preproc/xmlpreproc_config.ini.template')
        mock_get_registered_issues.return_value = [
            "abc v1n1"
        ]
        main()
        mock_send_mail.assert_called_once_with(
            "SciELO TESTE",
            "marca@example.com", "sysadm@example.com",
            "infras@example.com, prod@example.com",
            "Erros encontrados",
            '',
            "xmlpreproc_outs_msg_email.txt"
        )

    @patch("scilistatest_and_coletaxml.get_registered_issues")
    @patch("scilistatest_and_coletaxml.file_readlines")
    @patch("scilistatest_and_coletaxml.send_mail")
    @patch("scilistatest_and_coletaxml.XMLSerial.make_title_and_issue_updated")
    @patch("scilistatest_and_coletaxml.config_filepath")
    def test_main_send_email_with_errors_because_item_is_not_registered(
            self,
            mock_config_filepath,
            mock_update,
            mock_send_mail,
            mock_readlines,
            mock_get_registered_issues):
        mock_readlines.side_effect = [
            [],
            ["abc v1n1",
             ],
        ]
        mock_config_filepath.return_value = (
            'xml_preproc/xmlpreproc_config.ini.template')
        mock_get_registered_issues.return_value = [
            "abc v1n2"
        ]
        main()
        mock_send_mail.assert_called_once_with(
            "SciELO TESTE",
            "marca@example.com", "sysadm@example.com",
            "infras@example.com, prod@example.com",
            "Erros encontrados",
            '',
            "xmlpreproc_outs_msg_email.txt"
        )

    @patch("scilistatest_and_coletaxml.XMLSerial._check_db_status")
    @patch("scilistatest_and_coletaxml.get_registered_issues")
    @patch("scilistatest_and_coletaxml.file_readlines")
    @patch("scilistatest_and_coletaxml.send_mail")
    @patch("scilistatest_and_coletaxml.XMLSerial.make_title_and_issue_updated")
    @patch("scilistatest_and_coletaxml.config_filepath")
    def test_main_send_email_with_errors_because__check_db_status_returned_error(
            self,
            mock_config_filepath,
            mock_update,
            mock_send_mail,
            mock_readlines,
            mock_get_registered_issues,
            mock_check_db):
        mock_check_db.return_value = {
            "error_msg":
            "xmlserial/abc/v1n1/base/v1n1.mst nao encontrada"}
        mock_readlines.side_effect = [
            [],
            ["abc v1n1",
             ],
        ]
        mock_config_filepath.return_value = (
            'xml_preproc/xmlpreproc_config.ini.template')
        mock_get_registered_issues.return_value = [
            "abc v1n1"
        ]
        main()
        mock_send_mail.assert_called_once_with(
            "SciELO TESTE",
            "marca@example.com", "sysadm@example.com",
            "infras@example.com, prod@example.com",
            "Erros encontrados",
            '',
            "xmlpreproc_outs_msg_email.txt"
        )

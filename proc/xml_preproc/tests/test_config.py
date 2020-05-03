from unittest import TestCase
from unittest.mock import patch, mock_open

from xml_preproc.config import Config


class TestConfig(TestCase):

    def setUp(self):
        self.content = {
            'COLLECTION': 'SciELO TESTE',
            'XML_SERIAL_LOCATION_SERVER': 'server',
            'XML_SERIAL_LOCATION_USER': 'user',
            'XML_SERIAL_LOCATION': '/bases/collection.000/serial',
            'TMP_LOCATION': '/tmp',
            'MAIL_TO': 'marca@example.com',
            'MAIL_CC': 'infras@example.com, prod@example.com',
            'MAIL_BCC': 'bcc@example.com',
        }

    def test_init_raises_os_error(self):
        self.assertRaises(
            OSError,
            Config,
            'not_a_file.ini'
        )

    @patch("xml_preproc.config.read")
    def test_check_returns_error_because_of_missing_collection(
            self, mock_read):
        del self.content['COLLECTION']
        mock_read.return_value = self.content

        config = Config("xmlpreproc_config.ini.template")
        expected = (
            'xmlpreproc_config.ini.template: Falta valor para COLLECTION')
        errors = config.check()
        self.assertEqual(errors, expected)

    @patch("xml_preproc.config.read")
    def test_check_returns_error_because_of_missing_xml_serial_location(
            self, mock_read):
        del self.content['XML_SERIAL_LOCATION']
        mock_read.return_value = self.content

        config = Config("xmlpreproc_config.ini.template")
        expected = ((
            'xmlpreproc_config.ini.template: '
            'Falta valor para XML_SERIAL_LOCATION'))
        errors = config.check()
        self.assertEqual(errors, expected)

    @patch("xml_preproc.config.read")
    def test_check_returns_error_because_of_missing_tmp_location(
            self, mock_read):
        del self.content['TMP_LOCATION']
        mock_read.return_value = self.content

        config = Config("xmlpreproc_config.ini.template")
        expected = (
            'xmlpreproc_config.ini.template: Falta valor para TMP_LOCATION')
        errors = config.check()
        self.assertEqual(errors, expected)

    @patch("xml_preproc.config.read")
    def test_check_returns_error_because_of_missing_mailto(
            self, mock_read):
        del self.content['MAIL_TO']
        mock_read.return_value = self.content

        config = Config("xmlpreproc_config.ini.template")
        expected = ((
            'xmlpreproc_config.ini.template: '
            'Falta valor para MAIL_TO'))
        errors = config.check()
        self.assertEqual(errors, expected)

    @patch("xml_preproc.config.read")
    def test_check_returns_error_because_of_missing_mailcc(
            self, mock_read):
        del self.content['MAIL_CC']
        mock_read.return_value = self.content

        config = Config("xmlpreproc_config.ini.template")
        expected = ((
            'xmlpreproc_config.ini.template: '
            'Falta valor para MAIL_CC'))
        errors = config.check()
        self.assertEqual(errors, expected)

    @patch("xml_preproc.config.logger.info")
    @patch("xml_preproc.config.read")
    def test_check_log_info_because_of_missing_mailbcc(
            self, mock_read, mock_logger_info):
        del self.content['MAIL_BCC']
        mock_read.return_value = self.content

        config = Config("xmlpreproc_config.ini.template")
        expected = ((
            'xmlpreproc_config.ini.template: '
            'Nenhum valor para MAIL_BCC (opcional)'))
        config.check()
        mock_logger_info.assert_called_once_with(expected)

    @patch("xml_preproc.config.logger.info")
    @patch("xml_preproc.config.read")
    def test_check_log_info_because_of_missing_server(
            self, mock_read, mock_logger_info):
        del self.content['XML_SERIAL_LOCATION_SERVER']
        mock_read.return_value = self.content

        config = Config("xmlpreproc_config.ini.template")
        expected = ((
            'xmlpreproc_config.ini.template: '
            'Nenhum valor para XML_SERIAL_LOCATION_SERVER (opcional)'))
        config.check()
        mock_logger_info.assert_called_once_with(expected)

    @patch("xml_preproc.config.logger.info")
    @patch("xml_preproc.config.read")
    def test_check_log_info_because_of_missing_user(
            self, mock_read, mock_logger_info):
        del self.content['XML_SERIAL_LOCATION_USER']
        mock_read.return_value = self.content

        config = Config("xmlpreproc_config.ini.template")
        expected = ((
            'xmlpreproc_config.ini.template: '
            'Nenhum valor para XML_SERIAL_LOCATION_USER (opcional)'))
        config.check()
        mock_logger_info.assert_called_once_with(expected)



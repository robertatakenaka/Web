#!/usr/bin/env python2.7
# coding: utf-8
import os
import logging
import logging.config


logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)


def read(filepath):
    logger.info("Arquivo de configuracao %s" % filepath)
    items = {}
    with open(filepath) as fp:
        for row in fp.readlines():
            logger.info(row.strip())
            if row.startswith("#"):
                continue
            if '=' in row:
                name, value = row.strip().split("=")
                items[name] = value
    return items


class Config:

    def __init__(self, config_filepath):
        self.config_filepath = config_filepath
        self.collection_path = os.path.dirname(os.path.dirname(os.getcwd()))
        self._config = read(config_filepath)
        self.REQUIRED = (
            'COLLECTION',
            'XML_SERIAL_LOCATION',
            'TMP_LOCATION',
            'MAIL_TO',
            'MAIL_CC',
            )
        self.OPTIONAL = (
            'XML_SERIAL_LOCATION_SERVER',
            'XML_SERIAL_LOCATION_USER',
            'MAIL_BCC',
            )

    def get(self, name):
        return self._config.get(name)

    def check(self):
        errors = [
            '{}: Falta valor para {}'.format(
                self.config_filepath, k, self.get(k))
            for k in self.REQUIRED
            if not self.get(k)
        ]
        for k in self.OPTIONAL:
            if not self.get(k):
                logger.info('%s: Nenhum valor para %s (opcional)' % (
                    self.config_filepath, k))
        if errors:
            return "\n".join(errors)

#!/usr/bin/env python2.7
# coding: utf-8
import os
from . import fs_commands
from .fs_commands import (
    fileinfo,
    file_delete,
    file_readlines,
    os_system,
)


def get_sorted_list_and_repeated_items(list_items, sorted_function=sorted):
    repeated = []
    _sorted = sorted_function(list_items)
    if len(list_items) > len(_sorted):
        repeated = [
            (item, list_items.count(item))
            for item in _sorted
        ]
    return _sorted, repeated


# mx_pft(PROCISSUEDB, PFT, REGISTERED_ISSUES_FILENAME)
def mx_pft(base, PFT, display=False):
    """
    Check the issue database
    Return a list of registered issues
    """
    result = './mx_pft.tmp'
    if os.path.isfile(result):
        file_delete(result)
    cmd = 'mx {} "pft={}" now | sort -u > {}'.format(base, PFT, result)
    os_system(cmd, display)
    r = file_readlines(result)
    file_delete(result)
    return r or []


def db_filename(local, acron, issueid, extension=''):
    return '{}/{}/{}/base/{}{}'.format(
        local, acron, issueid, issueid, extension)


def get_articles(base):
    """
    Check the issue database
    Return a list of registered issues
    """
    return mx_pft(base, "if v706='h' then v702/ fi") or []


class XMLSerial:

    def __init__(self, config, logger, proc_serial):
        self.cfg = config
        self.fs = fs_commands.FSCommands(self.remote)
        self._serial_path = self.cfg.get("XML_SERIAL_LOCATION")
        self.logger = logger
        self.proc_serial = proc_serial

    @property
    def remote(self):
        if self.cfg.get('server'):
            return fs_commands.Remote(
                self.cfg.get('server'), self.cfg.get('user'))

    @property
    def serial_path(self):
        return self.fs.path(self._serial_path)

    def create_local_copy(self, db_filename, new_name):
        if self.remote:
            dest = "/tmp/{}".format(os.path.basename(db_filename))
            self.fs.scp(db_filename+".mst", dest+".mst")
            self.fs.scp(db_filename+".xrf", dest+".xrf")
            return dest
        return db_filename

    def copy(self, folder, dest, nohup=False):
        source = os.path(self.serial_path, folder)
        cmd = self.fs.copy(source, dest)
        fs_commands.run(cmd, nohup)

    def rsync(self, folder, dest, nohup=False):
        source = os.path(self.serial_path, folder)
        cmd = self.fs.rsync(source, dest)
        fs_commands.run(cmd, nohup)

    def exists(self, path):
        return self.fs.exists(path)

    @property
    def issue_db_path(self):
        return '{}/issue/issue'.format(self.serial_path)

    def get_most_recent_title_issue_databases(self):
        # v1.0 scilistatest.sh [8-32]
        """
        Check which title/issue/code bases are more recent:
            - from proc serial
            - from XML serial
        if from XML, copy the databases to serial folder
        """
        self.logger.info(
            'XMLPREPROC: Seleciona as bases title e issue mais atualizada')
        self.logger.info(
            'XMLPREPROC: Copia as bases title e issue de %s' %
            self.cfg.get('XML_SERIAL_LOCATION'))
        for folder in ['title', 'issue']:
            self.rsync(folder, self.proc_serial)

    def check_scilista_items_db(self, registered_items):
        # v1.0 scilistatest.sh [41] (checkissue.py)
        self.logger.info('SCILISTA TESTE %i itens' % len(registered_items))
        valid_issue_db = []
        for acron, issueid in registered_items:
            db_status = self._check_db_status(acron, issueid)
            error_msg = db_status.get("error_msg")
            if error_msg:
                self.logger.error(error_msg)
            else:
                valid_issue_db.append(db_status)
        return valid_issue_db

    def _check_db_status(self, acron, issueid):
        """
        Check the existence of acron/issue databases in XML serial
        If the database is ahead and it exists in serial folder,
        they should be merged
        Return a dict:
            items_to_copy: bases to copy from XML serial to serial
            mx_append: commands to merge aop
            error_msg: error message
            files_info: files which have to be in serial
        """
        xml_db_filename = db_filename(self.serial_path, acron, issueid)
        xml_mst_filename = xml_db_filename + '.mst'
        proc_db_filename = db_filename(self.proc_serial, acron, issueid)
        proc_mst_filename = proc_db_filename + '.mst'

        status = {}
        if not self.exists(xml_mst_filename):
            status["error_msg"] = 'Not found {}'.format(xml_mst_filename)
            return status

        status["files_info"] = [
            (f, fileinfo(f))
            for f in [proc_mst_filename, proc_db_filename+'.xrf']
        ]
        mx_append = None
        if 'nahead' in issueid and os.path.exists(proc_mst_filename):
            mx_append = self._check_ahead_db_status(
                proc_db_filename, xml_db_filename)
        if mx_append:
            status["mx_append"] = mx_append
        else:
            status["items_to_copy"] = (xml_db_filename, proc_db_filename)

    def _check_ahead_db_status(self, proc_db_filename, xml_db_filename):
        """
        Verifica a existencia das base ahead na area de processamento e
        na area do xc
        Caso existam as duas bases, verificar seu conteudo.
        - verificar se a base na area de proc esta com documentos repetidos
        - verificar se na base do xc ha documentos diferentes do que esta em proc,
          se afirmativo, retorna o comando para fazer o append
        """
        msg = 'Encontradas duas bases nahead \n {}\n {}.'.format(
                xml_db_filename, proc_db_filename)

        proc_aop = get_articles(proc_db_filename)
        proc_sorted, proc_rep = get_sorted_list_and_repeated_items(proc_aop)
        if proc_rep:
            self.logger.error('Ha duplicacoes em %s ' % proc_db_filename)
            for doc, q in proc_rep:
                self.logger.error('Repetido %s: %i vezes' % (doc, q))
        else:
            local_xml_db = self.create_local_copy(
                xml_db_filename, proc_db_filename + '_tmp')

            xml_aop = get_articles(local_xml_db)
            repeated = set(xml_aop).intersection(set(proc_aop))
            if not repeated:
                # fazer append
                self.logger.info('COLETA XML: %s Executara o append' % msg)
                return 'mx {} from=2 append={} -all now'.format(
                            local_xml_db,
                            proc_db_filename
                        )
            self.logger.info((
                'COLETA XML: %s '
                'Desnecessario executar append pois tem mesmo conteudo' %
                msg
            ))

    def update_proc_serial(self, items_info):
        # v1.0 coletaxml.sh [16] (getbasesxml4proc.py)
        items_info = items_info or []
        self.logger.info('COLETA XML: Coletar %i itens' % len(items_info))
        for item in items_info:
            items_to_copy = item.get("items_to_copy")
            mx_append = item.get("mx_append")
            if items_to_copy:
                xml_item, proc_item = items_to_copy
                self._copy_to_proc_serial(xml_item, proc_item)
            elif mx_append:
                self.logger.info('COLETA XML: %s' % mx_append)
                os_system(mx_append)

    def _copy_to_proc_serial(self, xml_item, proc_item):
        self.logger.info('COLETA XML: %s %s' % (xml_item, proc_item))
        xml_mst_filename = xml_item+'.mst'
        xml_xrf_filename = xml_item+'.xrf'
        proc_mst_filename = proc_item+'.mst'
        proc_xrf_filename = proc_item+'.xrf'

        path = os.path.dirname(proc_mst_filename)
        if not os.path.isdir(path):
            os.makedirs(path)
        self.rsync(xml_mst_filename, proc_mst_filename)
        self.rsync(xml_xrf_filename, proc_xrf_filename)

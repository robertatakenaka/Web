#!/usr/bin/env python2.7
# coding: utf-8
import os
import fs_commands
from fs_commands import (
    fileinfo,
    file_delete,
    file_readlines,
    os_system,
)


def get_sorted_list_and_repeated_items(list_items, sorted_function=sorted):
    repeated = tuple()
    _sorted = tuple(sorted_function(set(list_items)))
    if len(list_items) > len(_sorted):
        repeated = tuple(
            (item, list_items.count(item))
            for item in _sorted
            if list_items.count(item) > 1
        )
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


def get_documents(base):
    """
    Check the issue database
    Return a list of registered issues
    """
    return mx_pft(base, "if v706='h' then v702/ fi") or []


class AOPChecker(object):

    def __init__(self, proc_db_filepath, xml_db_filepath):
        self.proc_db_filepath = proc_db_filepath
        self.xml_db_filepath = xml_db_filepath

    def check_db_status(self):
        """
        Caso existam as duas bases, verificar seu conteudo.
        - retorna erro se a base na area de proc esta com documentos repetidos
        - se as bases xml e proc sao diferentes retornar o comando mx append
        """
        proc_aop = get_documents(self.proc_db_filepath)
        return (
            self._find_repeatitions(proc_aop) or
            self._compare(proc_aop, get_documents(self.xml_db_filepath))
        )

    def _find_repeatitions(self, proc_aop):
        """
        Verificar se a base na area de proc esta com documentos repetidos
        """
        proc_sorted, proc_rep = get_sorted_list_and_repeated_items(proc_aop)
        if proc_rep:
            errors = [
                'Em %s %s ocorre %i vezes' % (self.proc_db_filepath, doc, q)
                for doc, q in proc_rep
            ]
            return {
                "error_msg": "\n".join(errors)
            }
        return {}

    def _compare(self, proc_aop, xml_aop):
        """
        Verifica se o conteudo de xml_aop esta em proc_aop, ou seja,
        se proc_aop ja esta atualizado
        """
        if xml_aop and not set(xml_aop).intersection(set(proc_aop)):
            return {
                "mx_append":
                'mx {} from=2 append={} -all now'.format(
                    self.xml_db_filepath,
                    self.proc_db_filepath
                )
            }
        return {}


class XMLSerial(object):

    def __init__(self, config, proc_serial):
        self.cfg = config
        self.fs = fs_commands.FSCommands(
            self.cfg.get('server'), self.cfg.get('user'))
        self._serial_path = self.cfg.get("XML_SERIAL_LOCATION")
        self.proc_serial = proc_serial
        self.TMP_LOCATION = self.cfg.get("TMP_LOCATION", "/tmp")

    @property
    def serial_path(self):
        return self.fs._path(self._serial_path)

    def synchronize(self, folder, dest, nohup=False):
        path = os.path.dirname(dest)
        if not os.path.isdir(path):
            os.makedirs(path)

        source = os.path.join(self.serial_path, folder)
        cmd = self.fs.rsync(source, dest)
        fs_commands.run(cmd, nohup)

    def exists(self, path):
        return self.fs.exists(path)

    @property
    def issue_db_path(self):
        return '{}/issue/issue'.format(self.serial_path)

    def make_title_and_issue_updated(self):
        # v1.0 scilistatest.sh [8-32]
        """
        Check which title/issue/code bases are more recent:
            - from proc serial
            - from XML serial
        if from XML, copy the databases to serial folder
        """
        for folder in ['title', 'issue']:
            self.synchronize(folder, self.proc_serial)

    def check_scilista_items_db(self, registered_items, logger):
        # v1.0 scilistatest.sh [41] (checkissue.py)
        valid_issue_db = []
        for acron, issueid in set(registered_items):
            db_status = self._check_db_status(acron, issueid)
            error_msg = db_status.get("error_msg")
            if error_msg:
                logger.error(error_msg)
            else:
                valid_issue_db.append(db_status)
        return valid_issue_db

    def _get_aop_xml_db_filepath(self, xml_db_filepath, acron, issueid):
        if ":" in xml_db_filepath:
            tmp = os.path.join(self.TMP_LOCATION, acron, issueid)
            self.synchronize(xml_db_filepath, tmp)
            return tmp
        return xml_db_filepath

    def _check_db_status(self, acron, issueid):
        """
        Check the existence of acron/issue databases in XML serial
        If the database is ahead and it exists in serial folder,
        check whether it has to be merged or replaced or do nothing
        Return a dict:
            items_to_copy: bases to copy from XML serial to serial
            mx_append: command to merge both aop databases
            error_msg: error message
            files_info: files expected to be in serial at the end
        """
        xml_db_filepath = db_filename(self.serial_path, acron, issueid)
        xml_mst_filename = xml_db_filepath + '.mst'
        if not self.exists(xml_mst_filename):
            return {"error_msg": 'Not found {}'.format(xml_mst_filename)}

        proc_db_filepath = db_filename(self.proc_serial, acron, issueid)
        proc_mst_filename = proc_db_filepath + '.mst'

        status = {}
        status["files_info"] = [
            (f, fileinfo(f))
            for f in [proc_mst_filename, proc_db_filepath+'.xrf']
        ]
        if 'nahead' in issueid and os.path.exists(proc_mst_filename):
            xml_db_filepath = self._get_aop_xml_db_filepath(
                xml_db_filepath, acron, issueid)
            aop_checker = AOPChecker(proc_db_filepath, xml_db_filepath)
            status.update(aop_checker.check_db_status())
        if not status.get("mx_append"):
            status["items_to_copy"] = (xml_db_filepath, proc_db_filepath)
        return status

    def update_proc_serial(self, items_info, logger):
        # v1.0 coletaxml.sh [16] (getbasesxml4proc.py)
        items_info = items_info or []
        logger.info('COLETA XML: Coletar %i itens' % len(items_info))
        for item in items_info:
            items_to_copy = item.get("items_to_copy")
            if items_to_copy:
                xml_item, proc_item = items_to_copy
                logger.info('COLETA XML: copy %s %s' % (xml_item, proc_item))
                self._copy_to_proc_serial(xml_item, proc_item)
                continue
            mx_append = item.get("mx_append")
            if mx_append:
                logger.info('COLETA XML: %s' % mx_append)
                os_system(mx_append)

    def _copy_to_proc_serial(self, xml_item, proc_item):
        xml_mst_filename = xml_item+'.mst'
        xml_xrf_filename = xml_item+'.xrf'
        proc_mst_filename = proc_item+'.mst'
        proc_xrf_filename = proc_item+'.xrf'
        self.synchronize(xml_mst_filename, proc_mst_filename)
        self.synchronize(xml_xrf_filename, proc_xrf_filename)

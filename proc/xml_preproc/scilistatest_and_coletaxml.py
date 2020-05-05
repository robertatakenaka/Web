#!/usr/bin/env python2.7
# coding: utf-8
import platform
import os
import logging
import logging.config

from datetime import datetime
from copy import deepcopy

from xml_preproc.config import Config
from xml_preproc.fs_commands import (
    fileinfo,
    file_read,
    file_readlines,
    file_write,
    file_delete,
    os_system,
)
from xml_preproc.xml_serial import (
    XMLSerial,
    mx_pft,
    get_sorted_list_and_repeated_items,
)


logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)


REGISTERED_ISSUES_PFT = "v930,' ',if v32='ahead' then v65*0.4, fi,|v|v31,|s|v131,|n|v32,|s|v132,v41/"
LOG_FILE = 'xmlpreproc_outs.log'
ERROR_FILE = 'xmlpreproc_outs_scilista-erros.txt'
PROC_SERIAL_LOCATION = '../serial'
SCILISTA_XML = '{}/scilistaxml.lst'.format(PROC_SERIAL_LOCATION)
SCILISTA = '{}/scilista.lst'.format(PROC_SERIAL_LOCATION)
PROCISSUEDB = '{}/issue/issue'.format(PROC_SERIAL_LOCATION)


def scilista_info(name, scilista_items):
    rows = []
    _sorted = sorted(scilista_items)
    name1 = "{} original ({} itens)".format(name, len(scilista_items))
    name2 = "{} ordenada ({} itens)".format(name, len(_sorted))

    rows.append(_scilista_info(name1, scilista_items))
    rows.append(_scilista_info(name2, _sorted))

    return "\n".join(rows)


def _scilista_info(name, scilista_items):
    rows = []
    rows.append("")
    rows.append(name)
    rows.append('='*len(name))
    rows.append("")
    rows.extend(scilista_items)
    rows.append("")
    return "\n".join(rows)


def validate_scilista_item_format(row):
    parts = row.split()
    if len(parts) == 2:
        return parts
    if len(parts) == 3 and parts[-1] == 'del':
        return parts


def sort_scilista(scilista_items):
    items = list(set([item.strip() for item in scilista_items]))
    dellist = []
    prlist = []
    naheadlist = []
    issuelist = []
    for item in items:
        if item.endswith('del'):
            dellist.append(item)
        elif item.endswith('pr'):
            prlist.append(item)
        elif item.endswith('nahead'):
            naheadlist.append(item)
        else:
            issuelist.append(item)
    return sorted(dellist) + sorted(prlist) + sorted(naheadlist) + sorted(issuelist)


def join_scilistas_and_update_scilista_file(scilistaxml_items, scilista_items):
    # v1.0 coletaxml.sh [20] (joinlist.py)
    new_scilista_items = sort_scilista(scilistaxml_items + scilista_items)
    content = '\n'.join(new_scilista_items)+'\n'
    file_write(SCILISTA, content)
    logger.info('JOIN SCILISTAS: %s + %s' % (SCILISTA, SCILISTA_XML))
    logger.info(content)


def items_to_retry_updating(items):
    try_again = []
    logger.info('COLETA XML: Verificar se coleta foi bem sucedida')
    for item in items:
        for info in item["files_info"]:
            path, status = info
            if fileinfo(path) == status:
                try_again.append(item)
                break
    return try_again


class ProcSerial(object):

    def __init__(self, xmlserial):
        self.xmlserial = xmlserial

    def update_title_and_issue(self):
        # Garante que title e issue na pasta de processamento estao atualizadas
        logger.info('Deixa as bases title e issue atualizadas em proc')
        self.xmlserial.make_title_and_issue_updated()

    @property
    def registered_issues(self):
        """
        Check the issue database
        Return the list of registered issues
        """
        items = []
        if os.path.isfile(PROCISSUEDB+'.mst'):
            items = mx_pft(PROCISSUEDB, REGISTERED_ISSUES_PFT)
        _registered_issues = []
        for item in items:
            parts = item.strip().split()
            if len(parts) == 2:
                _registered_issues.append(parts[0].lower() + ' ' + parts[1])
        if not _registered_issues:
            logger.error("A base %s esta corrompida ou ausente" % PROCISSUEDB)
        return _registered_issues

    def registered_scilista_items(self, scilista_items):
        # Verificar se os itens da scilistaxml sao issues registrados
        # v1.0 scilistatest.sh [41] (checkissue.py)
        logger.info(
            'Verifica se %i itens estao registrados' % len(scilista_items))
        _registered_scilista_items = []
        for item in scilista_items:
            issue = '{} {}'.format(acron, issueid)
            # v1.0 scilistatest.sh [41] (checkissue.py)
            if issue in self.registered_issues:
                if (acron, issueid) not in _registered_scilista_items:
                    _registered_scilista_items.append((acron, issueid))
            else:
                logger.error('"%s" nao esta registrado' % issue)
        return _registered_scilista_items


        registered_scilista_items = check_scilista_items_are_registered(
            sorted_items, registered_issues)
        logger.info(
            '%s: %i itens registrados' % (self.scilistaxml_filepath, len(registered_scilista_items)))

    def check_scilista_items_db(self, registered_items):
        db_items = self._check_scilista_items_db(registered_items)
        if len(db_items) == len(registered_items):
            self._get_db_items(db_items)
            return True

    def _check_scilista_items_db(self, registered_items):
        db_items, errors = self.xmlserial.check_scilista_items_db(
            registered_items)
        for err in errors:
            logger.error(err)
        return db_items

    def _get_db_items(self, db_items):
        # estando scilista completamente valida,
        # entao coleta os dados dos issues
        # verifica se as bases dos artigos estao presentes na area de proc
        items = deepcopy(db_items)
        for i in range(1, 4):
            self.xmlserial.update_proc_serial(db_items)
            items = items_to_retry_updating(items)
            if len(items) == 0:
                break
            # tenta atualizar aquilo que não pode ser atualizado
        logger.info("Coleta: %i tentativa(s)" % i)
        if len(items) == 0:
            logger.info("Coleta completa.")
            return True

        logger.error("Coleta incompleta.")
        for item in items:
            for f in item["files_info"]:
                logger.error('Nao coletado: %s' % f[0])


class ScilistaXML(object):

    def __init__(self, scilistaxml_items, scilistaxml_filepath):
        self.scilistaxml_items = scilistaxml_items
        self.qtd_items = len(scilistaxml_items)
        self.scilistaxml_filepath = scilistaxml_filepath

    def _find_conflicting_items(self):
        conflicts = []
        for item in self.valid_items:
            if len(item) == 3 and item[:-1] in self.valid_items:
                d = " ".join(item)
                a = " ".join(item[:-1])
                conflicts.append((a, d))
                logger.error((
                    "Encontrados '%s' e '%s' na scilistaxml. "
                    "Mantenha apenas um. "
                    "Mantenha '%s' para atualizar. "
                    "Mantenha '%s' para nao ser publicado."
                    ) % (a, d, a, d))
        return conflicts

    @property
    def valid_items(self):
        _valid_items = []
        for item in self.scilistaxml_items:
            parts = validate_scilista_item_format(item)
            if parts:
                _valid_items.append(parts)
            else:
                logger.error('"%s" tem formato invalido' % item)
        return _valid_items

    def check_items(self):
        # Verifica se a scilistaxml esta vazia
        if not self.scilistaxml_items:
            logger.error(
                '%s vazia ou nao encontrada' % self.scilistaxml_filepath)
            return

        logger.info(
            '%s: %i itens na lista' % (
                self.scilistaxml_filepath, self.qtd_items))

        # Remove os itens del se tambem ha os mesmos itens para adicionar
        conflicts = self._find_conflicting_items()
        if conflicts:
            logger.error(
                ('%s contem itens conflitantes. '
                 'Verificar e enviar novamente.' % self.scilistaxml_filepath))

        # Verificar se ha repeticao
        sorted_items, repeated = get_sorted_list_and_repeated_items(
            self.scilistaxml_items)
        if repeated:
            logger.error(
                ('%s contem itens repetidos. '
                 'Verificar e enviar novamente.' % self.scilistaxml_filepath))

        return sorted_items, conflicts, repeated

    def check_scilista_xml_and_coleta_xml(self):
        # Verificar se os itens da scilistaxml sao issues registrados
        registered_items = check_scilista_items_are_registered(
            sorted_items, registered_issues)
        logger.info(
            '%s: %i itens registrados' % (self.scilistaxml_filepath, len(registered_items)))

        db_items = self._check_scilista_items_db(registered_items)

        if repeated or conflicts or len(db_items) < self.qtd_items:
            return False
        else:
            self._get_db_items(db_items)
            return True


class SciListaXML(object):

    def __init__(self, scilistaxml_items, xmlserial):
        self.scilistaxml_items = scilistaxml_items
        self.qtd_items = len(scilistaxml_items)
        self.xmlserial = xmlserial

    def _find_conflicting_items(self):
        dellist = [i for i in self.scilistaxml_items if i.endswith("del")]
        conflicts = []
        for i in dellist:
            if i[:-4] in self.scilistaxml_items:
                conflicts.append((i[:-4], i))
                logger.error((
                    "Encontrados '%s' e '%s' na scilistaxml. "
                    "Mantenha apenas um. "
                    "Mantenha '%s' para atualizar. "
                    "Mantenha '%s' para nao ser publicado."
                    ) % (i[:-4], i, i[:-4], i))
        return conflicts

    def _check_scilista_items_db(self, registered_items):
        db_items, errors = self.xmlserial.check_scilista_items_db(
            registered_items)
        for err in errors:
            logger.error(err)
        return db_items

    def _get_db_items(self, db_items):
        # estando scilista completamente valida,
        # entao coleta os dados dos issues
        # verifica se as bases dos artigos estao presentes na area de proc
        items = deepcopy(db_items)
        for i in range(1, 4):
            self.xmlserial.update_proc_serial(db_items)
            items = items_to_retry_updating(items)
            if len(items) == 0:
                break
            # tenta atualizar aquilo que não pode ser atualizado
        logger.info("Coleta: %i tentativa(s)" % i)
        if len(items) == 0:
            logger.info("Coleta completa.")
            return True

        logger.error("Coleta incompleta.")
        for item in items:
            for f in item["files_info"]:
                logger.error('Nao coletado: %s' % f[0])

    def check_scilista_xml_and_coleta_xml(self):
        # Garante que title e issue na pasta de processamento estao atualizadas
        logger.info('Deixa as bases title e issue atualizadas em proc')
        self.xmlserial.make_title_and_issue_updated()

        # Verifica se a scilistaxml esta vazia
        if not self.scilistaxml_items:
            logger.error('%s vazia ou nao encontrada' % SCILISTA_XML)
            print('%s vazia ou nao encontrada' % SCILISTA_XML)
            return

        logger.info(
            '%s: %i itens na lista' % (
                SCILISTA_XML, self.qtd_items))

        # Remove os itens del se tambem ha os mesmos itens para adicionar
        conflicts = self._find_conflicting_items()
        if conflicts:
            logger.error(('%s contem itens conflitantes. '
                          'Verificar e enviar novamente.' % SCILISTA_XML))

        # Verificar se ha repeticao
        sorted_items, repeated = get_sorted_list_and_repeated_items(
            self.scilistaxml_items)
        if repeated:
            logger.error(('%s contem itens repetidos. '
                          'Verificar e enviar novamente.' % SCILISTA_XML))

        # Retorna uma lista de issues registrados
        registered_issues = get_registered_issues()
        if not registered_issues:
            logger.error("A base %s esta corrompida ou ausente" % PROCISSUEDB)
            return

        # Verificar se os itens da scilistaxml sao issues registrados
        registered_items = check_scilista_items_are_registered(
            sorted_items, registered_issues)
        logger.info(
            '%s: %i itens registrados' % (SCILISTA_XML, len(registered_items)))

        db_items = self._check_scilista_items_db(registered_items)

        if repeated or conflicts or len(db_items) < self.qtd_items:
            return False
        else:
            self._get_db_items(db_items)
            return True


class Report(object):
    def __init__(self, scilista_datetime, proc_datetime, config):
        self.scilista_datetime = scilista_datetime or ''
        self.proc_datetime = proc_datetime
        self.config = config
        self.errors = file_read(ERROR_FILE).replace("\x00", "")
        self.email_msg_file = 'xmlpreproc_outs_msg_email.txt'

    def send_mail(self, subject):
        mailbcc = self.config.get("MAIL_BCC")
        _mailbcc = '-b "{}"'.format(mailbcc) if mailbcc else ''
        _subject = '[XML PREPROC][{}][{}] {}'.format(
                self.config.get("COLLECTION"),
                self.scilista_datetime[:10],
                subject
            )
        cmd = 'mailx {} {} -c "{}" -s "{}" < {}'.format(
                self.config.get("MAIL_TO"),
                _mailbcc,
                self.config.get("MAIL_CC"),
                _subject,
                self.email_msg_file
            )
        os_system(cmd)

    def create_msg_instructions(self):
        if self.errors:
            fim = ''
            instructions = [
                "Foram encontrados erros no procedimento de coleta de XML. ",
                "Veja abaixo.",
                "Caso o erro seja na scilistaxml ou fasciculo nao registrado, "
                "faca as correcoes e solicite o processamento novamente.",
                "Caso contrario, aguarde instrucoes.",
                "",
                "Erros",
                "-----",
                "{}".format(self.errors),
            ]
            instructions = "\n".join(instructions)
        else:
            instructions = (
                "Nenhum erro encontrado. "
                "Processamento sera iniciado em breve.")
            fim = '[pok]'
        return instructions, fim

    def get_email_message(self, instructions, scilistas, fim):
        rows = [
            "ATENCAO: Mensagem automatica. Nao responder a este e-mail.",
            "Prezados,",
            "Colecao: {}".format(self.config.get("COLLECTION")),
            "Data   da scilista:    {}".format(self.scilista_datetime),
            "Inicio da verificacao: {}".format(self.proc_datetime),
            "{}".format(instructions),
            "{}".format(scilistas),
            "----",
            "{}".format(fim)
        ]
        return "\n".join(rows)

    def create_msg_file(self, scilistas):
        file_write(self.email_msg_file)
        instructions, fim = self.create_msg_instructions()
        msg = self.get_email_message(instructions, scilistas, fim)
        file_write(self.email_msg_file, msg)
        logger.info(msg)

    def gera_relatorio(self, scilistaxml_items, scilistahtml_items):
        if self.errors:
            subject = 'Erros encontrados'
            next_action = 'Fazer correcoes'
        else:
            subject = 'OK'
            next_action = 'Executar processar.sh'

        scilistas = scilista_info("scilista XML", scilistaxml_items)
        scilistas += scilista_info("scilista HTML", scilistahtml_items)

        # v1.0 scilistatest.sh [43-129]
        self.create_msg_file(scilistas)
        self.send_mail(subject)
        return next_action


def collection_dirname():
    curr = os.getcwd()
    folders = curr.split('/')
    # ['', 'bases', 'col.xxx']
    return folders[2]


def config_filepath():
    return 'xmlpreproc_config_{}.ini'.format(collection_dirname())


def main():
    file_write(ERROR_FILE)
    start_datetime = datetime.now().isoformat().replace('T', ' ')[:-7]
    logger.info('XMLPREPROC: INICIO %s' % start_datetime)

    CONFIG = Config(config_filepath())
    errors = CONFIG.check()
    if errors:
        exit(errors)

    logger.info('%s %s' % (CONFIG.get('COLLECTION'), start_datetime))
    logger.info('dir local: %s' % os.getcwd())

    xml_scilista_datetime = None
    xml_scilista_items = []
    htm_scilista_items = file_readlines(SCILISTA)

    if os.path.isfile(SCILISTA_XML):
        xml_scilista_datetime = datetime.fromtimestamp(
            os.path.getmtime(SCILISTA_XML)).isoformat().replace('T', ' ')

    xml_scilista_items = file_readlines(SCILISTA_XML)
    xmlserial = XMLSerial(CONFIG, PROC_SERIAL_LOCATION)
    scilistaxml = SciListaXML(xml_scilista_items, xmlserial)
    if scilistaxml.check_scilista_xml_and_coleta_xml():
        # atualiza a scilista na area de processamento
        join_scilistas_and_update_scilista_file(
            xml_scilista_items, htm_scilista_items)

    report = Report(xml_scilista_datetime, start_datetime, CONFIG)
    next_action = report.gera_relatorio(xml_scilista_items, htm_scilista_items)

    # v1.0 coletaxml.sh [21-25]
    print("Proximo passo:")
    print(next_action)
    file_write(ERROR_FILE)

if __name__ == "__main__":
    main()

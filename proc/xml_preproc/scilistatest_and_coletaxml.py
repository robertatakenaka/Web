#!/usr/bin/env python2.7
# coding: utf-8
import os
import ConfigParser
from datetime import datetime
import logging
from copy import deepcopy

from .fs_commands import (
    fileinfo,
    file_read,
    file_readlines,
    file_write,
    os_system,
)
from xml_serial import (
    XMLSerial,
    mx_pft,
    get_sorted_list_and_repeated_items,
)


REGISTERED_ISSUES_PFT = "v930,' ',if v32='ahead' then v65*0.4, fi,|v|v31,|s|v131,|n|v32,|s|v132,v41/"
LOG_FILE = 'xmlpreproc_outs.log'
ERROR_FILE = 'xmlpreproc_outs_scilista-erros.txt'
PROC_SERIAL_LOCATION = '../serial'
SCILISTA_XML = '{}/scilistaxml.lst'.format(PROC_SERIAL_LOCATION)
SCILISTA = '{}/scilista.lst'.format(PROC_SERIAL_LOCATION)
PROCISSUEDB = '{}/issue/issue'.format(PROC_SERIAL_LOCATION)


logger = logging.getLogger(__name__)


class Config:

    def __init__(self, collection_dirname):
        self.config = None
        self.collection_dirname = collection_dirname

    def load(self):
        try:
            self.config = ConfigParser.ConfigParser()
            with open(self.file_path) as fp:
                self.config.readfp(fp)
        except OSError as e:
            print(("Falta arquivo de configuração: {}. "
                   "Consulte o modelo: {}").format(
                    self.file_path, 'xmlpreproc_config.ini.template'
                ))
            raise e
        except ConfigParser.MissingSectionHeaderError as e:
            raise e

    @property
    def file_path(self):
        return 'xmlpreproc_config_{}.ini'.format(self.collection_dirname)

    def get(self, name):
        return self.config.get("[SECTION]", name)

    def check(self):
        serial_path = "/{}/serial".format(self.collection_dirname)
        issue_path = os.path.join(self.get('XML_SERIAL_LOCATION'), 'issue')

        errors = []
        if serial_path not in self.get('XML_SERIAL_LOCATION'):
            errors.append(
                'Esperada a pasta "{}" em "{}"'.format(
                    serial_path, self.get('XML_SERIAL_LOCATION')))

        if not os.path.isdir(issue_path):
            errors.append(
                'Esperada a pasta "issue" em "{}"'.format(
                    self.get('XML_SERIAL_LOCATION')))
        if errors:
            raise(ValueError("\n".join(errors)))


def config_loggers():
    file_write(LOG_FILE)
    file_write(ERROR_FILE)
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh_errors = logging.FileHandler(ERROR_FILE)
    fh_errors.setLevel(logging.ERROR)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    fh_errors.setFormatter()
    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)
    logger.addHandler(fh_errors)


def get_registered_issues():
    """
    Check the issue database
    Return the list of registered issues of issue
    """
    items = []
    if os.path.isfile(PROCISSUEDB+'.mst'):
        items = mx_pft(PROCISSUEDB, REGISTERED_ISSUES_PFT)

    registered_issues = []
    for item in items:
        parts = item.strip().split()
        if len(parts) == 2:
            registered_issues.append(parts[0].lower() + ' ' + parts[1])
    return registered_issues


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


def check_scilista_items_are_registered(scilista_items, registered_issues):
    # v1.0 scilistatest.sh [41] (checkissue.py)
    logger.info('SCILISTA TESTE %i itens' % len(scilista_items))
    registered_items = []
    n = 0
    for item in scilista_items:
        n += 1
        parts = validate_scilista_item_format(item)
        if parts:
            acron, issueid = parts[0], parts[1]
            issue = '{} {}'.format(acron, issueid)
            # v1.0 scilistatest.sh [41] (checkissue.py)
            if issue in registered_issues:
                registered_items.append((acron, issueid))
            else:
                logger.error('Linha %i: "%s" nao esta registrado' % (n, issue))
        else:
            logger.error('Linha %i: "%s" tem formato invalido' % (n, item))
    return registered_items


def is_proc_serial_updated(items):
    try_again = []
    logger.info('COLETA XML: Verificar se coleta foi bem sucedida')
    for item in items:
        for info in item["files_info"]:
            path, status = info
            if fileinfo(path) == status:
                try_again.append(item)
                break
    return try_again


def check_scilista_xml_and_coleta_xml(scilistaxml_items, xmlserial):
    # Garante que title e issue na pasta de processamento estao atualizadas
    xmlserial.get_most_recent_title_issue_databases()

    # obtem lista de issues registrados
    registered_issues = get_registered_issues()
    if not registered_issues:
        logger.error("A base %s esta corrompida ou ausente" % PROCISSUEDB)
        return

    if not scilistaxml_items:
        logger.error('%s vazia ou nao encontrada' % SCILISTA_XML)
        return

    # verificar se ha repeticao
    sorted_items, repeated = get_sorted_list_and_repeated_items(
        scilistaxml_items)
    if repeated:
        logger.error(('%s contem itens repetidos. '
                      'Verificar e enviar novamente.' % SCILISTA_XML))

    registered_items = check_scilista_items_are_registered(
        sorted_items, registered_issues)

    valid_scilista_items = xmlserial.check_scilista_items_db(registered_items)

    if not repeated and len(valid_scilista_items) == len(scilistaxml_items):
        # estando scilista completamente valida,
        # entao coleta os dados dos issues
        xmlserial.update_proc_serial(valid_scilista_items)
        # verifica se as bases dos artigos estao presentes na area de proc
        items = deepcopy(valid_scilista_items)
        for i in range(0, 3):
            items = is_proc_serial_updated(items)
            if len(items) == 0:
                break
            # tenta atualizar aquilo que não pode ser atualizado
            xmlserial.update_proc_serial(items)
        if len(items) > 0:
            logger.error("Coleta incompleta")
            for item in items:
                for f in item["files_info"]:
                    logger.error('%s nao atualizado' % f)
        return True


def scilista_info(name, scilista_items):
    rows = []
    name = "{} ({} itens)".format(name, len(scilista_items))
    _sorted, repeated = get_sorted_list_and_repeated_items(
        scilista_items, sort_scilista)

    rows.append(name)
    rows.append('='*len(name))
    rows.append('')
    rows.extend(_sorted)
    rows.append("")
    if repeated:
        rows.append("Repetidos")
        rows.extend(["{} ({}}x)".format(item, qtd) for item, qtd in repeated])
        rows.append("")
    return "\n".join(rows)


def send_mail(mailto, mailbcc, mailcc, subject, scilista_date, email_msg_file):
    if CONFIG.get('TEST') is True:
        mailto = CONFIG.get('MAIL_TO_TEST')
        mailcc = CONFIG.get('MAIL_TO_TEST')
        mailbcc = CONFIG.get('MAIL_TO_TEST')

    _mailbcc = '-b "{}"'.format(mailbcc) if mailbcc else ''
    _subject = '[XML PREPROC][{}][{}] {}'.format(
            CONFIG.get('COLLECTION'),
            scilista_date[:10],
            subject
        )
    cmd = 'mailx {} {} -c "{}" -s "{}" < {}'.format(
            mailto,
            _mailbcc,
            mailcc,
            _subject,
            email_msg_file
        )
    os_system(cmd)


def create_msg_instructions(errors):
    instructions = "Nenhum erro encontrado. Processamento sera iniciado em breve."
    fim = '[pok]'
    if errors:
        fim = ''
        instructions = """
Foram encontrados erros no procedimento de coleta de XML.
Veja abaixo.
Caso o erro seja na scilistaxml ou fasciculo nao registrado,
faca as correcoes e solicite o processamento novamente.
Caso contrario, aguarde instrucoes.

Erros
-----
{}
    """.format(errors)
    return instructions, fim


def get_email_message(scilista_date, proc_date, instructions, numbers, fim):
    return """
    ATENCAO: Mensagem automatica. Nao responder a este e-mail.

Prezados,

Colecao: {}
Data   da scilista:    {}
Inicio da verificacao: {}

{}


{}

----
{}
    """.format(
        CONFIG.get('COLLECTION'),
        scilista_date,
        proc_date,
        instructions,
        numbers,
        fim
        )


def create_msg_file(scilista_date, proc_date, errors, scilistas):
    email_msg_file = 'xmlpreproc_outs_msg_email.txt'
    file_write(email_msg_file)
    errors = errors or ''
    instructions, fim = create_msg_instructions(errors)
    msg = get_email_message(
        scilista_date, proc_date, instructions, scilistas, fim)
    file_write(email_msg_file, msg)
    logger.info(msg)
    return email_msg_file


def report(SCILISTA_DATETIME, PROC_DATETIME,
           scilistaxml_items, scilistahtml_items):
    errors = file_read(ERROR_FILE)
    subject = 'OK'
    next_action = 'Executar processar.sh'
    if errors:
        subject = 'Erros encontrados'
        next_action = 'Fazer correcoes'

    scilistas = scilista_info(scilistaxml_items)
    scilistas += scilista_info(scilistahtml_items)

    # v1.0 scilistatest.sh [43-129]
    email_msg_file = create_msg_file(
        SCILISTA_DATETIME, PROC_DATETIME, errors, scilistas)
    send_mail(CONFIG.get('MAIL_TO'), CONFIG.get('MAIL_BCC'),
              CONFIG.get('MAIL_CC'), subject, SCILISTA_DATETIME,
              email_msg_file)

    return next_action


def collection_dirname():
    curr = os.getcwd()
    folders = curr.split('/')
    # ['', 'bases', 'col.xxx']
    return folders[2]


if __name__ == "__main__":
    config_loggers()
    start_datetime = datetime.now().isoformat().replace('T', ' ')[:-7]
    logger.info('XMLPREPROC: INICIO %s' % start_datetime)

    CONFIG = Config(collection_dirname())
    try:
        CONFIG.load()
        CONFIG.check()
    except (OSError, ValueError, ConfigParser.MissingSectionHeaderError) as e:
        exit(e)

    logger.info('%s %s' % (CONFIG.get('COLLECTION'), start_datetime))
    logger.info('dir local: %s' % os.getcwd())

    xml_scilista_datetime = datetime.fromtimestamp(
                os.path.getmtime(SCILISTA_XML)).isoformat().replace('T', ' ')
    os_system('dos2unix {}'.format(SCILISTA_XML))
    xml_scilista_items = file_readlines(SCILISTA_XML)
    htm_scilista_items = file_readlines(SCILISTA)

    xmlserial = XMLSerial(CONFIG)
    if check_scilista_xml_and_coleta_xml(xml_scilista_items, xmlserial):
        # atualiza a scilista na area de processamento
        join_scilistas_and_update_scilista_file(
            xml_scilista_items, htm_scilista_items)

    next_action = report(xml_scilista_datetime, start_datetime,
                         xml_scilista_items, htm_scilista_items)

    # v1.0 coletaxml.sh [21-25]
    logger.info("Proximo passo:")
    logger.info(next_action)
    exit(next_action)

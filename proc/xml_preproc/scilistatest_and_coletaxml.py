#!/usr/bin/env python2.7
# coding: utf-8
import os
import time
import shutil
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
                if (acron, issueid) not in registered_items:
                    registered_items.append((acron, issueid))
            else:
                logger.error('Linha %i: "%s" nao esta registrado' % (n, issue))
        else:
            logger.error('Linha %i: "%s" tem formato invalido' % (n, item))
    return registered_items


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


def find_conflicting_items(scilistaxml_items):
    dellist = [i for i in scilistaxml_items if i.endswith("del")]
    conflicts = []
    for i in dellist:
        if i[:-4] in scilistaxml_items:
            conflicts.append((i[:-4], i))
            logger.error((
                "Encontrados '%s' e '%s' na scilistaxml. "
                "Mantenha '%s' para atualizar. "
                "Mantenha '%s' para nao ser publicado."
                ) % (i[:-4], i, i[:-4], i))
    return conflicts


def check_scilista_xml_and_coleta_xml(scilistaxml_items, xmlserial):
    # Garante que title e issue na pasta de processamento estao atualizadas
    logger.info('Deixa as bases title e issue atualizadas em proc')
    xmlserial.make_title_and_issue_updated()

    # Verifica se a scilistaxml esta vazia
    if not scilistaxml_items:
        logger.error('%s vazia ou nao encontrada' % SCILISTA_XML)
        print('%s vazia ou nao encontrada' % SCILISTA_XML)
        return

    logger.info(
        '%s: %i itens na lista' % (SCILISTA_XML, len(scilistaxml_items)))

    # Remove os itens del se tambem ha os mesmos itens para adicionar
    conflicts = find_conflicting_items(scilistaxml_items)
    if conflicts:
        logger.error(('%s contem itens conflitantes. '
                      'Verificar e enviar novamente.' % SCILISTA_XML))

    # Verificar se ha repeticao
    sorted_items, repeated = get_sorted_list_and_repeated_items(
        scilistaxml_items)
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

    db_items, errors = xmlserial.check_scilista_items_db(registered_items)
    for err in errors:
        logger.error(err)

    if repeated or conflicts or len(db_items) < len(scilistaxml_items):
        return False
    else:
        # estando scilista completamente valida,
        # entao coleta os dados dos issues
        xmlserial.update_proc_serial(db_items, logger)
        # verifica se as bases dos artigos estao presentes na area de proc
        items = deepcopy(db_items)
        for i in range(0, 3):
            items = items_to_retry_updating(items)
            if len(items) == 0:
                break
            # tenta atualizar aquilo que não pode ser atualizado
            xmlserial.update_proc_serial(items)
        if len(items) > 0:
            logger.error("Coleta incompleta")
            for item in items:
                for f in item["files_info"]:
                    logger.error('Nao coletado: %s' % f[0])
        return True


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


def send_mail(collection, mailto, mailbcc, mailcc, subject, scilista_date, email_msg_file):
    _mailbcc = '-b "{}"'.format(mailbcc) if mailbcc else ''
    _subject = '[XML PREPROC][{}][{}] {}'.format(
            collection,
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
    if errors:
        fim = ''
        instructions = (
            "Foram encontrados erros no procedimento de coleta de XML. "
            "Veja abaixo. \n"
            "Caso o erro seja na scilistaxml ou fasciculo nao registrado, "
            "faca as correcoes e solicite o processamento novamente. \n"
            "Caso contrario, aguarde instrucoes. \n"
            "\n"
            "Erros\n"
            "-----\n"
            "{}\n"
            ).format(errors)
    else:
        instructions = (
            "Nenhum erro encontrado. "
            "Processamento sera iniciado em breve.")
        fim = '[pok]'

    return instructions, fim


def get_email_message(
        collection, scilista_date, proc_date, instructions, numbers, fim):
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
        collection,
        scilista_date,
        proc_date,
        instructions,
        numbers,
        fim
        )


def create_msg_file(collection, scilista_date, proc_date, errors, scilistas):
    email_msg_file = 'xmlpreproc_outs_msg_email.txt'
    file_write(email_msg_file)
    errors = errors or ''
    instructions, fim = create_msg_instructions(errors)
    msg = get_email_message(
        collection, scilista_date, proc_date, instructions, scilistas, fim)
    file_write(email_msg_file, msg)
    logger.info(msg)
    return email_msg_file


def report(scilista_datetime, proc_datetime,
           scilistaxml_items, scilistahtml_items, config):
    errors = file_read(ERROR_FILE)
    if errors:
        subject = 'Erros encontrados'
        next_action = 'Fazer correcoes'
    else:
        subject = 'OK'
        next_action = 'Executar processar.sh'

    scilistas = scilista_info("scilista XML", scilistaxml_items)
    scilistas += scilista_info("scilista HTML", scilistahtml_items)

    # v1.0 scilistatest.sh [43-129]
    email_msg_file = create_msg_file(
        config.get('COLLECTION'), scilista_datetime, proc_datetime, errors,
        scilistas)
    send_mail(
        config.get('COLLECTION'), config.get('MAIL_TO'),
        config.get('MAIL_BCC'), config.get('MAIL_CC'), subject,
        scilista_datetime or '', email_msg_file)

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
        os_system('dos2unix {}'.format(SCILISTA_XML))

    xml_scilista_items = file_readlines(SCILISTA_XML)
    xmlserial = XMLSerial(CONFIG, PROC_SERIAL_LOCATION)
    if check_scilista_xml_and_coleta_xml(xml_scilista_items, xmlserial):
        # atualiza a scilista na area de processamento
        join_scilistas_and_update_scilista_file(
            xml_scilista_items, htm_scilista_items)

    next_action = report(xml_scilista_datetime, start_datetime,
                         xml_scilista_items, htm_scilista_items, CONFIG)

    # v1.0 coletaxml.sh [21-25]
    print("Proximo passo:")
    print(next_action)
    file_write(ERROR_FILE)

if __name__ == "__main__":
    main()

#!/usr/bin/env python2.7
# coding: utf-8
import os
import shutil
import ConfigParser
from datetime import datetime
import logging


class Config:

    def __init__(self):
        self.config = None

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
    def collection_dirname(self):
        curr = os.getcwd()
        folders = curr.split('/')
        # ['', 'bases', 'col.xxx']
        return folders[2]

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


REGISTERED_ISSUES_PFT = "v930,' ',if v32='ahead' then v65*0.4, fi,|v|v31,|s|v131,|n|v32,|s|v132,v41/"
LOG_FILE = 'xmlpreproc_outs.log'
ERROR_FILE = 'xmlpreproc_outs_scilista-erros.txt'
EMAIL_MSG_FILE = 'xmlpreproc_outs_msg_email.txt'
PROC_DATETIME = datetime.now().isoformat().replace('T', ' ')[:-7]


CONFIG = Config()
try:
    CONFIG.load()
    CONFIG.check()
except (OSError, ValueError, ConfigParser.MissingSectionHeaderError) as e:
    exit(e)


logger = logging.getLogger(__name__)
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
fh_errors.setFormatter(formatter)
# add the handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)
logger.addHandler(fh_errors)

PROC_SERIAL_LOCATION = '../serial'
REGISTERED_ISSUES_FILENAME = '{}/registered_issues.txt'.format(PROC_SERIAL_LOCATION)
SCILISTA_XML = '{}/scilistaxml.lst'.format(PROC_SERIAL_LOCATION)
SCILISTA = '{}/scilista.lst'.format(PROC_SERIAL_LOCATION)
PROCISSUEDB = '{}/issue/issue'.format(PROC_SERIAL_LOCATION)
XMLISSUEDB = '{}/issue/issue'.format(CONFIG.get('XML_SERIAL_LOCATION'))


def os_system(cmd, display=True):
    """
    Execute a command
    """
    msg = '_'*30 + '\n#  Executando: \n#    >>> {}'.format(cmd)
    logger.info(msg)
    os.system(cmd)


def fileinfo(filename):
    """
    Return mtime, size of a file
    """
    if os.path.isfile(filename):
        return os.path.getmtime(filename), os.path.getsize(filename)
    return 0, 0


def get_more_recent_title_issue_databases():
    # v1.0 scilistatest.sh [8-32]
    """
    Check which title/issue/code bases are more recent:
        - from proc serial
        - from XML serial
    if from XML, copy the databases to serial folder
    """
    logger.info('XMLPREPROC: Seleciona as bases title e issue mais atualizada')
    xmlf_date, xmlf_size = fileinfo(XMLISSUEDB+'.mst')
    proc_date, proc_size = fileinfo(PROCISSUEDB+'.mst')
    if not proc_size or proc_date < xmlf_date:
        logger.info(
            'XMLPREPROC: Copia as bases title e issue de %s' %
            CONFIG.get('XML_SERIAL_LOCATION'))
        for folder in ['title', 'issue']:
            os_system(
                'cp -r {}/{} {}'.format(
                    CONFIG.get('XML_SERIAL_LOCATION'),
                    folder,
                    PROC_SERIAL_LOCATION
                    )
                )
    else:
        logger.info(
            'XMLPREPROC: Use as bases title e issue de %s' %
            PROC_SERIAL_LOCATION)


def file_delete(filename, raise_exc=False):
    try:
        os.unlink(filename)
    except OSError as e:
        if raise_exc:
            raise e
        print(e)


def file_write(filename, content=''):
    path = os.path.dirname(filename)
    if path and not os.path.isdir(path):
        os.makedirs(path)
    with open(filename, "w") as fp:
        fp.write(content)


def file_read(filename):
    try:
        with open(filename, "r") as fp:
            c = fp.read()
    except OSError:
        return None
    else:
        return c


def file_readlines(filename):
    try:
        with open(filename, "r") as fp:
            c = [i.strip() for i in fp.readlines()]
    except OSError:
        return []
    else:
        return c


def validate_scilista_item_format(row):
    parts = row.split()
    if len(parts) == 2:
        return parts
    if len(parts) == 3 and parts[-1] == 'del':
        return parts


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


def db_filename(local, acron, issueid, extension=''):
    return '{}/{}/{}/base/{}{}'.format(
        local, acron, issueid, issueid, extension)


def get_articles(base):
    """
    Check the issue database
    Return a list of registered issues
    """
    return mx_pft(base, "if v706='h' then v702/ fi") or []


def check_ahead_db_status(proc_db_filename, xml_db_filename):
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

    xml_aop = get_articles(xml_db_filename)
    proc_aop = get_articles(proc_db_filename)

    items = set(proc_aop)
    if len(proc_aop) > len(items):
        logger.error('Ha duplicacoes em %s ' % proc_db_filename)
        for doc in items:
            q = proc_aop.count(doc)
            if q > 1:
                logger.error('Repetido %s: %i vezes' % (doc, q))
    else:
        repeated = False
        for item in xml_aop:
            if item in proc_aop:
                repeated = True
                break
        if repeated is False:
            # fazer append
            logger.info('COLETA XML: %s Executara o append' % msg)
            return 'mx {} from=2 append={} -all now'.format(
                        xml_db_filename,
                        proc_db_filename
                    )
        logger.info((
            'COLETA XML: %s '
            'Desnecessario executar append pois tem mesmo conteudo' %
            msg
        ))


def check_db_status(acron, issueid):
    """
    Check the existence of acron/issue databases in XML serial
    If the database is ahead and it exists in serial folder,
    they should be merged
    Return a dict:
        items_to_copy: bases to copy from XML serial to serial
        mx_append_db_commands: commands to merge aop
        error_msg: error message
        expected_db_files_in_serial: list of files which have to be in serial
    """
    xml_db_filename = db_filename(
        CONFIG.get('XML_SERIAL_LOCATION'), acron, issueid)
    xml_mst_filename = xml_db_filename + '.mst'
    proc_db_filename = db_filename(PROC_SERIAL_LOCATION, acron, issueid)
    proc_mst_filename = proc_db_filename + '.mst'

    status = {}
    status["expected_db_files_in_serial"] = [
        proc_mst_filename, proc_db_filename+'.xrf']
    if os.path.exists(xml_mst_filename):
        mx_append_db_commands = None
        if 'nahead' in issueid and os.path.exists(proc_mst_filename):
            mx_append_db_commands = check_ahead_db_status(
                proc_db_filename, xml_db_filename)
        if mx_append_db_commands:
            status["mx_append_db_commands"] = mx_append_db_commands
        else:
            status["items_to_copy"] = (xml_db_filename, proc_db_filename)
    else:
        status["error_msg"] = 'Not found {}'.format(xml_mst_filename)
    return status


def coletaxml(xml_item, proc_item):
    xml_mst_filename = xml_item+'.mst'
    proc_mst_filename = proc_item+'.mst'
    xml_xrf_filename = xml_item+'.xrf'
    proc_xrf_filename = proc_item+'.xrf'

    errors = []
    if os.path.exists(xml_mst_filename):
        path = os.path.dirname(proc_mst_filename)
        if not os.path.isdir(path):
            os.makedirs(path)
        if os.path.isdir(path):
            shutil.copyfile(xml_mst_filename, proc_mst_filename)
            shutil.copyfile(xml_xrf_filename, proc_xrf_filename)
        else:
            errors.append('Nao foi possivel criar {}'.format(path))
    if not os.path.exists(proc_mst_filename):
        errors.append('Nao foi possivel criar {}'.format(proc_mst_filename))
    if not os.path.exists(proc_xrf_filename):
        errors.append('Nao foi possivel criar {}'.format(proc_xrf_filename))
    if len(errors) > 0:
        logger.error('\n'.join(errors))
        return False
    return True


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


def send_mail(mailto, mailbcc, mailcc, subject, scilista_date):
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
            EMAIL_MSG_FILE
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
    errors = errors or ''
    instructions, fim = create_msg_instructions(errors)
    msg = get_email_message(
        scilista_date, proc_date, instructions, scilistas, fim)

    file_write(EMAIL_MSG_FILE, msg)
    logger.info(msg)


def get_scilista_sorted_and_repeated_items(scilista_name, scilista_items):
    repeated = []
    _sorted = sort_scilista(scilista_items)
    if len(scilista_items) > len(_sorted):
        repeated = [
            (item, scilista_items.count(item))
            for item in _sorted
        ]
    return _sorted, repeated


def check_scilista_items_are_registered(scilista_items, registered_issues):
    # v1.0 scilistatest.sh [41] (checkissue.py)
    logger.info('SCILISTA TESTE %i itens' % len(scilista_items))
    valid_issues_data = []
    n = 0
    for item in scilista_items:
        n += 1
        parts = validate_scilista_item_format(item)
        if parts:
            acron, issueid = parts[0], parts[1]
            issue = '{} {}'.format(acron, issueid)

            # v1.0 scilistatest.sh [41] (checkissue.py)
            if issue not in registered_issues:
                logger.error('Linha %i: "%s" nao esta registrado' % (n, issue))
            else:
                db_status = check_db_status(acron, issueid)
                error_msg = db_status.get("error_msg")
                if error_msg:
                    logger.error('Linha %i: %s' % (n, error_msg))
                else:
                    valid_issues_data.append(db_status)
        else:
            logger.error('Linha %i: "%s" tem formato invalido' % (n, item))
    return valid_issues_data


def coletar_items(coleta_items):
    # v1.0 coletaxml.sh [16] (getbasesxml4proc.py)
    expected = []
    coleta_items = coleta_items or []
    logger.info('COLETA XML: Coletar %i itens' % len(coleta_items))
    for item in coleta_items:
        items_to_copy = item.get("items_to_copy")
        mx_append_db_command = item.get("mx_append_db_command")
        expected.extend(item.get("expected_db_files_in_serial", []))
        if items_to_copy:
            xml_item, proc_item = items_to_copy
            coletaxml(xml_item, proc_item)
        elif mx_append_db_command:
            logger.info('COLETA XML: %s' % mx_append_db_command)
            os_system(mx_append_db_command)
    return expected


def check_coletados(expected):
    coletaxml_ok = True
    logger.info('COLETA XML: Verificar se coleta foi bem sucedida')
    for file in expected:
        if not os.path.exists(file):
            coletaxml_ok = False
            logger.error('Coleta incompleta. Falta %s' % file)
    return coletaxml_ok


def join_scilistas_and_update_scilista_file(scilistaxml_items, scilista_items):
    # v1.0 coletaxml.sh [20] (joinlist.py)
    new_scilista_items = sort_scilista(scilistaxml_items + scilista_items)
    content = '\n'.join(new_scilista_items)+'\n'
    file_write(SCILISTA, content)
    logger.info('JOIN SCILISTAS: %s + %s' % (SCILISTA, SCILISTA_XML))
    logger.info(content)


def check_scilista_xml(registered_issues):
    # v1.0 scilistatest.sh [6]
    os_system('dos2unix {}'.format(SCILISTA_XML))

    scilistaxml_items = file_readlines(SCILISTA_XML)
    if not scilistaxml_items:
        logger.error('%s vazia ou nao encontrada' % SCILISTA_XML)
        return

    sorted_items = sort_scilista(scilistaxml_items)
    if len(sorted_items) != len(scilistaxml_items):
        logger.error((
            '%s contem itens repetidos.'
            ' Verificar e enviar novamente.' % SCILISTA_XML))
        return

    # v1.0 scilistatest.sh
    # v1.0 scilistatest.sh [36] (scilistatest.py)
    valid_scilista_items = check_scilista_items_are_registered(
        scilistaxml_items, registered_issues)
    # v1.0 coletaxml.sh
    if len(valid_scilista_items) == len(scilistaxml_items):
        return sorted_items


def check_scilista_xml_and_coleta_xml():
    # Garante que title e issue na pasta de processamento estao atualizadas
    get_more_recent_title_issue_databases()

    # obtem lista de issues registrados
    registered_issues = get_registered_issues()
    if not registered_issues:
        logger.error("A base %s esta corrompida ou ausente" % PROCISSUEDB)
        return

    # verificar o conteúdo da scilista xml contra os issues registrados
    scilistaxml_items = check_scilista_xml(registered_issues)
    if scilistaxml_items:
        # estando completamente valida coleta os dados dos issues
        expected = coletar_items(scilistaxml_items)
        # verifica se as bases dos artigos estao presentes na area de proc
        check_coletados(expected)

        scilista_items = file_readlines(SCILISTA)
        # atualiza a scilista na area de processamento
        scilista_items = join_scilistas_and_update_scilista_file(
                scilistaxml_items, scilista_items)


def scilista_info(name, scilista_items):
    rows = []
    name = "{} ({} itens)".format(name, len(scilista_items))
    _sorted, repeated = get_scilista_sorted_and_repeated_items(
        name, scilista_items)

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


def report(SCILISTA_DATETIME, scilista_items, scilistaxml_items, scilistahtml_items):
    errors = file_read(ERROR_FILE)
    subject = 'OK'
    next_action = 'Executar processar.sh'
    if len(errors) > 0:
        subject = 'Erros encontrados'
        next_action = 'Fazer correcoes'

    scilistas = scilista_info(scilistaxml_items)
    scilistas += scilista_info(scilistahtml_items)

    # v1.0 scilistatest.sh [43-129]
    create_msg_file(SCILISTA_DATETIME, PROC_DATETIME, errors, scilistas)
    send_mail(CONFIG.get('MAIL_TO'), CONFIG.get('MAIL_BCC'),
              CONFIG.get('MAIL_CC'), subject, SCILISTA_DATETIME)

    return next_action


logger.info('XMLPREPROC: INICIO')
logger.info('%s %s' % (CONFIG.get('COLLECTION'), PROC_DATETIME))
logger.info('dir local: %s' % os.getcwd())

file_write(ERROR_FILE)
file_write(LOG_FILE)
if not os.path.isfile(SCILISTA):
    file_write(SCILISTA)
for f in [EMAIL_MSG_FILE]:
    file_delete(f)


expected = []
comments = ''
SCILISTA_DATETIME = None
scilistaxml_items = []
q_scilistaxml_items = 0
if os.path.exists(SCILISTA_XML):

    scilista_items = file_readlines(SCILISTA)

    SCILISTA_DATETIME = datetime.fromtimestamp(
                os.path.getmtime(SCILISTA_XML)).isoformat().replace('T', ' ')

    # v1.0 scilistatest.sh [6]
    os_system('dos2unix {}'.format(SCILISTA_XML))

    scilistaxml_items = file_readlines(SCILISTA_XML)
    q_scilistaxml_items = len(scilistaxml_items)

    logger.info('XMLPREPROC: SCILISTA')
    logger.info(SCILISTA_DATETIME)

    get_more_recent_title_issue_databases()

    registered_issues = get_registered_issues()
    if registered_issues:
        # v1.0 scilistatest.sh
        valid_scilista_items = check_scilista_items_are_registered(
            scilistaxml_items, registered_issues)
        # v1.0 coletaxml.sh
        if len(valid_scilista_items) == len(scilista_items):
            expected = coletar_items(valid_scilista_items)
            if check_coletados(expected):
                scilista_items = join_scilistas_and_update_scilista_file(
                    scilistaxml_items, scilista_items)
    else:
        logger.error("A base %s esta corrompida ou ausente" % PROCISSUEDB)

else:
    logger.error('Not found: %s ' % SCILISTA_XML)


errors = file_read(ERROR_FILE)
subject = 'OK'
next_action = 'Executar processar.sh'
if len(errors) > 0:
    subject = 'Erros encontrados'
    next_action = 'Fazer correcoes'

diffs = list_diff(scilista_items, scilistaxml_items)

comments = '{}: {} itens\n{}: {} itens ({} nao XML)'.format(
    SCILISTA_XML,
    q_scilistaxml_items,
    SCILISTA,
    len(scilista_items),
    len(diffs))

diffs = '' if len(diffs) == 0 else 'Conteudo de scilista.lst nao XML ({})\n{}\n'.format(len(diffs), '-'*len('Conteudo de scilista.lst nao XML')) + '\n'.join(diffs) + '\n'

# v1.0 scilistatest.sh [43-129]
msg_filename = create_msg_file(SCILISTA_DATETIME, PROC_DATETIME, errors, comments, diffs)
send_mail(CONFIG.get('MAIL_TO'), CONFIG.get('MAIL_BCC'), CONFIG.get('MAIL_CC'), subject, SCILISTA_DATETIME, msg_filename)

# v1.0 coletaxml.sh [21-25]
logger.info("Proximo passo:")
logger.info(next_action)
exit(next_action)

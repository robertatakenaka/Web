#!/usr/bin/env python2.7
# code = utf-8

import os
import shutil
import sys


class ScilistaItemBase(object):

    def __init__(self, serial_path, scilista_item):
        self.serial_path = serial_path
        self.scilista_item = scilista_item
        self.acron, self.issueid = self.scilista_item.split(' ')

    @property
    def issue_path(self):
        return self.serial_path + '/' + self.acron + '/' + self.issueid

    @property
    def base_path(self):
        return self.issue_path + '/base'

    @property
    def base_filename(self):
        return self.base_path + '/' + self.issueid

    @property
    def mst_filename(self):
        return self.base_filename + '.mst'


class Scilista(object):

    def __init__(self):
        self.scilista_items = []

    def load(self, filename):
        self.scilista_items = file_content_to_list(filename)

    @property
    def scilista_items(self):
        return [ScilistaItem(item) for item in self.scilista_items]

    @scilista_items.setter
    def scilista_items(self, l):
        self.scilista_items = l

    @property
    def organized(self):
        lists = {}
        for scilista_item in self.scilista_items:
            if scilista_item.value_type is not None:
                lists[scilista_item.value_type].append(scilista_item.value)
        r = []
        for value_type in ['del', 'pr', 'aop', 'other']:
            r.extend(sorted(list(set(lists[value_type]))))
        return r

    def validate(self, registered_items, dest_serial_path, src_serial_path=None):
        invalid_item = []
        invalid_base = []
        not_registered = []

        for scilista_item in self.scilista_items:
            if scilista_item.value_type is None:
                invalid_item.append(scilista_item.value)
            elif not scilista_item.value == 'del':
                if scilista_item.value in registered_items:
                    if src_serial_path is not None:
                        if scilista_item.get_base_xml_4proc(src_serial_path, dest_serial_path) is False:
                            invalid_base.append(scilista_item.value)
                    if scilista_item.valid_base(dest_serial_path) is False:
                        invalid_base.append(scilista_item.value)
                else:
                    not_registered.append(scilista_item.value)
        return (invalid_item, not_registered, invalid_base)


class ScilistaItem(object):

    def __init__(self, value):
        self._value = value
        self.parts = value.split(' ')

    @property
    def value(self):
        self._value = self._value.strip()
        parts = self._value.split(' ')
        return ' '.join([part for part in parts if part != ''])

    @property
    def value_type(self):
        _value_type = None
        parts = self.value.split(' ')
        if self.value.endswith(' del'):
            if len(parts) == 3:
                _value_type = 'del'
        elif len(parts) == 2:
            if self.value.endswith('pr'):
                _value_type = 'pr'
            elif self.value.endswith('nahead'):
                _value_type = 'aop'
            else:
                _value_type = 'other'
        return _value_type

    def get_base_xml_4proc(self, src_serial_path, dest_serial_path):
        write_log('INFO: Executando coleta de base XML de {item}'.format(item=self.item))
        not_found = None
        write_log('\n' + self.item)
        source = ScilistaItemBase(src_serial_path, self.value)
        if os.path.isfile(source.mst_filename):
            dest = ScilistaItemBase(dest_serial_path, self.value)
            if not os.path.isdir(dest.issue_path):
                os.makedirs(dest.issue_path)
            if self.value.endswith('nahead') and os.path.isfile(dest.mst_filename):
                if join_aop_bases(source.base_path, dest.issue_path):
                    write_log('juntou as bases {item}'.format(item=self.value))
                else:
                    write_log('ERRO: falhou ao juntar as bases {item}'.format(item=self.value))
            else:
                cmd = 'cp -rp {src} {dest}'.format(src=source.base_path, dest=dest.issue_path)
                if run_command(cmd):
                    write_log('copiou {item}'.format(item=self.value))
                else:
                    write_log('ERRO: falhou ao copiar {item}'.format(item=self.value))
        else:
            not_found = source.mst_filename
        return not_found

    def valid_base(self, dest_serial_path):
        dest = ScilistaItemBase(dest_serial_path, self.value)
        return os.path.isfile(dest.mst_filename)


def write_log(text, display=False):
    if text.startswith('ERRO') or text.startswith('INFO') or text.startswith('WARNING'):
        display = True
    if display:
        try:
            print(text)
        except:
            pass
    try:
        text = text.encode('utf-8')
        open('./preproc.log', 'a+').write(text + '\n')
    except:
        pass


def run_command(cmd):
    r = False
    try:
        os.system(cmd)
        r = True
    except Exception as e:
        write_log(u'ERRO: Não foi possível executar: ')
        write_log(cmd)
        try:
            write_log(str(e))
        except:
            pass
    return r


def join_aop_bases(src_base, dest_base):
    return run_command('mx {src} from=2 append={dest} -all now tell=50'.format(src=src_base, dest=dest_base))


def registered_issues(issue_db):
    registered_filename = './registered.txt'
    if os.path.isfile(registered_filename):
        os.unlink(registered_filename)
    pft = "v930,' ',if v32='ahead' then v65*0.4, fi,|v|v31,|s|v131,|n|v32,|s|v132,v41/ "
    cmd = 'mx ' + issue_db + ' ' + '"pft=' + pft + '" now | sort -u > ' + registered_filename
    run_command(cmd)
    return file_content_to_list(registered_filename)


def file_content_to_list(filename):
    content = ''
    if os.path.isfile(filename):
        content = open(filename, 'r').read().lower()
    return [item.strip() for item in content.split('\n') if item.strip() != '']


def validate(scilista_xml_filename, scilista_filename, issue_db, src_serial_path, dest_serial_path):
    write_log('Valida')
    registered_items = registered_issues(issue_db)

    scilista = Scilista()
    scilista.load(scilista_filename)
    invalid_items, not_registered, invalid_base = scilista.validate(registered_items, dest_serial_path)

    scilista_xml = Scilista()
    scilista_xml.load(scilista_xml_filename)
    xml_invalid_items, xml_not_registered, xml_invalid_base = scilista.validate(registered_items, dest_serial_path, src_serial_path)


def prepare():
    write_log('Pre processa')


if len(sys.argv) == 3:
    if validate():
        prepare()
else:
    print('Uso:')
    print('python2.7 coletaxml.py <scilista XML> <scilista>')
    print('')
    print('e.g:')
    print('python2.7 coletaxml.py ../serial/scilistaxml.lst ../serial/scilista.lst')


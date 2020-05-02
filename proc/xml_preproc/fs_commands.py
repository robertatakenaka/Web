import os


def os_system(cmd, display=True):
    """
    Execute a command
    """
    msg = '_'*30 + '\n#  Executando: \n#    >>> {}'.format(cmd)
    if display:
        print(msg)
        print(cmd)
    os.system(cmd)


def run(cmd, nohup=False):
    if nohup:
        cmd = "nohup {}&\n".format(cmd)
    os.system(cmd)


def fileinfo(filename):
    """
    Return mtime, size of a file
    """
    if os.path.isfile(filename):
        return os.path.getmtime(filename), os.path.getsize(filename)
    return 0, 0


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


class LocalCommands(object):
    def __init__(self):
        pass

    def _path(self, _path):
        return _path

    def exists(self, path):
        return os.path.exists(path)

    def mkdirs(self, path):
        return os.makedirs(path)

    def cp(self, src, dest):
        return "cp -r {} {}".format(src, dest)

    def rsync(self, src, dest, options="-apu"):
        """
        -C, --cvs-exclude
            auto-ignore files in the same way CVS does
        -r, --recursive
            recurse into directories
        -v, --verbose
            increase verbosity
        -p, --perms
            preserve permissions
        -a, --archive
            archive mode; equals -rlptgoD (no -H,-A,-X)
        -u, --update
            skip files that are newer on the receiver
        """
        return 'rsync {} {} {}'.format(options, src, dest)


class RemoteCommands(object):
    def __init__(self, server=None, user=None):
        self._server = server
        self._user = user
        self._port = None
        if server and ':' in server:
            self._server, self._port = server.split(':')

    @property
    def _rsync_port_param(self):
        return ' -e "ssh -p {}" '.format(self._port) if self._port else ''

    @property
    def _scp_port_param(self):
        return ' -P {} '.format(self._port) if self._port else ''

    @property
    def _ssh_port_param(self):
        return ' -p {} '.format(self._port) if self._port else ''

    @property
    def user_at(self):
        return "{}@".format(self._user) if self._user else ''

    def _path(self, _path):
        return "{}{}:{}".format(self.user_at, self._server, _path)

    def exists(self, path):
        return os.system('ssh {}{}{} "ls {}"'.format(
            self.user_at, self._server, self._ssh_port_param, path)) == 0

    def mkdirs(self, path):
        # 'ssh <USER>@<SERVER><PORT> "mkdir -p <PATH>"'
        return 'ssh {}{}{} "mkdir -p {}"'.format(
            self.user_at, self._server, self._ssh_port_param, path)

    def cp(self, src, dest):
        return "scp {} -r {} {}".format(
            self._scp_port_param, self._path(src), dest)

    def rsync(self, src, dest, options="-apu"):
        """
        -C, --cvs-exclude
            auto-ignore files in the same way CVS does
        -r, --recursive
            recurse into directories
        -v, --verbose
            increase verbosity
        -p, --perms
            preserve permissions
        -a, --archive
            archive mode; equals -rlptgoD (no -H,-A,-X)
        -u, --update
            skip files that are newer on the receiver
        """
        return 'rsync {} {} {} {}'.format(
            self._rsync_port_param, options, self._path(src), dest)


def FSCommands(server=None, user=None):
    if server:
        return RemoteCommands(server, user)
    return LocalCommands()

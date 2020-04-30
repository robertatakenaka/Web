import os


def run(cmd, nohup=False):
    if nohup:
        cmd = "nohup {}&\n".format(cmd)
    os.system(cmd)


class Remote(object):
    def __init__(self, server, user):
        self.server = server
        self.user = user
        self.port = None
        if ':' in server:
            self.server, self.port = server.split(':')

    def path(self, _path):
        return "{}@{}:{}".format(self.user, self.server, _path)

    def exists(self, path):
        # 'ssh <USER>@<SERVER><PORT> "ls <PATH>"'
        return os.system('ssh {}@{}{} "ls {}"'.format(
            self.user, self.server, self.ssh_port_param, path)) == 0

    @property
    def rsync_port_param(self):
        return ' -e "ssh -p {}" '.format(self.port) if self.port else ''

    @property
    def scp_port_param(self):
        return ' -P {} '.format(self.port) if self.port else ''

    @property
    def ssh_port_param(self):
        return ' -p {} '.format(self.port) if self.port else ''

    @property
    def mkdirs(self, path):
        # 'ssh <USER>@<SERVER><PORT> "mkdir -p <PATH>"'
        return 'ssh {}@{}{} "mkdir -p {}"'.format(
            self.user, self.server, self.ssh_port_param, path)

    @property
    def copy(self, src, dest):
        return "scp {} -r {} {}".format(self.scp_port_param, src, dest)


class FSCommands(object):

    def __init__(self, remote=None):
        self.remote = remote

    def path(self, _path):
        if self.remote:
            return self.remote.path(_path)
        return _path

    def exists(self, path):
        if self.remote:
            return self.remote.exists(path)
        return os.path.exists(path)

    @property
    def rsync_port_param(self):
        return self.remote.rsync_port_param if self.remote else ''

    def rsync(self, src, dest, options="-auvp"):
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
            self.rsync_port_param, options, src, dest)

    @property
    def cp(self, src, dest):
        if self.remote:
            self.remote.cp(src, dest)
        else:
            return "cp {} -r {} {}".format(self.scp_port_param, src, dest)

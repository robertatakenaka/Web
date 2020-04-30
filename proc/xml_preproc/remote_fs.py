import os


def run(cmd, nohup=False):
    if nohup:
        cmd = "nohup {}&\n".format(cmd)
    os.system(cmd)


class RemoteFS(object):

    def __init__(self, server, user):
        self.server = server
        self.user = user
        self.port = None
        if ':' in server:
            self.server, self.port = server.split(':')

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
    def command_remote_mkdirs(self, path):
        # 'ssh <USER>@<SERVER><PORT> "mkdir -p <PATH>"'
        return 'ssh {}@{}{} "mkdir -p {}"'.format(
            self.user, self.server, self.ssh_port_param, path)

    def remote_path(self, path):
        return "{}@{}:{}".format(self.user, self.server, path)

    def rsync(self, src, dest):
        return 'rsync {} -CrvK {} {}'.format(self.rsync_port_param, src, dest)

    @property
    def scp(self, src, dest):
        return "scp {} -r {} {}".format(self.scp_port_param, src, dest)

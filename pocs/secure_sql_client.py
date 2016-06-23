from sshtunnel import SSHTunnelForwarder

class SSQLClient(object):
    """docstring for SSQLClient"""
    def __init__(self, ssh_conf, db_conf, remote_conf=None):
        super(SSQLClient, self).__init__()

        assert ssh_conf['user'], 'ssh user must be specified'
        assert ssh_conf['pass'], 'ssh pass must be specified'
        assert ssh_conf['host'], 'ssh host must be specified'
        assert ssh_conf['port'], 'ssh port must be specified'
        if not remote_conf: remote_conf = ('127.0.0.1', 3306)
        assert len(remote_conf) == 2, 'Remote Config must be correctly specified'
        self._sshTunnelArgs = (
            (ssh_conf['host'], ssh_conf['port'])
        )
        self._sshTunnelKwargs = {
            'ssh_passwd': ssh_conf['pass'],
            'ssh_username': ssh_conf['user'],
            'remote_bind_address': remote_conf
        }
        self.testSSHTunnel()

        assert db_conf['user'], 'db user must be specified'
        assert db_conf['pass'], 'db pass must be specified'
        assert db_conf['name'], 'db name must be specified'

        self._dbConnectKwargs = {
            'host': db_conf.get('host', '127.0.0.1'),
            'user': db_conf['user'],
            'pass': db_conf['pass'],
            'name': db_conf['name']
        }

        self.testDBConnet()

    def testSSHTunnel(self):
        with SSHTunnelForwarder(
            *self._sshTunnelArgs,
            **self._sshTunnelKwargs
        ) as server:
            if(server):
                pass
        #todo this

    def testDBConnet(self):
        with SSHTunnelForwarder(
            *self._sshTunnelArgs,
            **self._sshTunnelKwargs
        ) as server:
            if(server):
                pass
        #todo this


    def getSelectTuple(self, query):
        with SSHTunnelForwarder(
            *self._sshTunnelArgs,
            **self._sshTunnelKwargs
        ) as server:
            if(server):
                pass
        #todo this
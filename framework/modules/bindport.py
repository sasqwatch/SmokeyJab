try:
    from framework.main import ModuleBase
except ImportError:
    pass


class BindPort(ModuleBase):
    @property
    def tags(self):
        return ['IntrusionSet5']

    @property
    def relative_delay(self):
        return 90

    @property
    def absolute_duration(self):
        # 60 minutes
        return 60 * 60

    def bind_port(self, port):
        import socket, time
        s = socket.socket()
        s.bind(('', port))
        s.listen(1)
        time.sleep(self.absolute_duration)
        return

    def do_run(self):
        port = int('${PORT}')
        pid = self.util_childproc(func=self.bind_port, args=(port,))
        self.hec_logger('Kicked off process to listen on a port', pid=pid, port=port)
        self.util_orphanwait(pid)

    def run(self):
        self.start()
        try:
            self.do_run()
        except Exception as e:
            self.hec_logger('Uncaught exception within module, exiting module gracefully', error=str(e),
                            severity='error')
        self.finish()

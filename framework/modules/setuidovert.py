try:
    from framework.main import ModuleBase
except ImportError:
    pass


class SetUidOvert(ModuleBase):
    @property
    def tags(self):
        return ['IntrusionSet2']

    @property
    def relative_delay(self):
        return 40

    @property
    def absolute_duration(self):
        return 24 * 60 * 60  # 1 day

    def do_run(self):
        import os, stat, shutil, time
        fname = '/tmp/bash'
        shutil.copyfile('/bin/sleep', fname)
        with open(fname, 'a+b') as f:
            f.seek(0, os.SEEK_END)
            f.write(self._banner.encode('utf-8'))
        os.chmod(fname, stat.S_ISUID | stat.S_IRWXU)
        self.hec_logger('Created setuid binary', filename=fname)
        time.sleep(self.absolute_duration)
        os.unlink(fname)

    def run(self):
        self.start()
        try:
            self.do_run()
        except Exception as e:
            self.hec_logger('Uncaught exception within module, exiting module gracefully', error=str(e),
                            severity='error')
        self.finish()

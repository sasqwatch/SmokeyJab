try:
    from framework.main import ModuleBase
except ImportError:
    pass

class UserAdd(ModuleBase):
    @property
    def tags(self):
        return ['IntrusionSet3']

    @property
    def needs_root(self):
        return True

    @property
    def relative_delay(self):
        return 55

    @property
    def absolute_duration(self):
        return 24 * 3600  # 1 day

    def do_run(self):
        import time
        from subprocess import check_call, PIPE
        username = '${USER_NAME}'
        cmd = 'useradd -m -c "{1}" -l -N -s /bin/false {0}'.format(username, self._banner.replace(':',''))
        try:
            check_call(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            self.hec_logger('Added a user', username=username)
        except Exception as e:
            self.hec_logger(str(e), severity='error')
            return
        time.sleep(self.absolute_duration)
        try:
            check_call('userdel -r {0}'.format(username), shell=True, stdout=PIPE, stderr=PIPE)
            self.hec_logger('Removed a user', username=username)
        except Exception as e:
            self.hec_logger(str(e), severity='error')

    def run(self):
        self.start()
        try:
            self.do_run()
        except Exception as e:
            self.hec_logger('Uncaught exception within module, exiting module gracefully', error=str(e),
                            severity='error')
        self.finish()

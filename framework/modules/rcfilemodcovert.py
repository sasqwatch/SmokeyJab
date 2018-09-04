try:
    from framework.main import ModuleBase
except ImportError:
    pass

class RcFileModCovert(ModuleBase):
    @property
    def tags(self):
        return ['IntrusionSet1']

    @property
    def needs_root(self):
        return True

    @property
    def relative_delay(self):
        return 5

    @property
    def absolute_duration(self):
        return 60 * 60

    @staticmethod
    def resolve_link(path):
        import os
        if os.path.islink(path):
            _path = os.readlink(path)
            if not _path.startswith('/'):
                _path = os.path.join(os.path.dirname(path), _path)
        else:
            _path = path
        return os.path.abspath(_path)

    def do_run(self):
        import os, time
        rclocal_path = self.resolve_link('/etc/rc.local')
        link_path = os.tempnam()
        try:
            os.link(rclocal_path, link_path)
            self.hec_logger('Created hardlink', link_path=link_path, file_path=rclocal_path)
            with open(link_path, 'a+') as f:
                f.seek(0)
                data = f.read()
                f.write('\n# ' + self._banner + '\n')
                offset = f.tell()
            self.hec_logger('Added content to the file', file_path=rclocal_path)
        except Exception as e:
            self.hec_logger(str(e), severity='error')
        else:
            # Wait one hour before restoring file
            time.sleep(self.absolute_duration)
            with open(link_path, 'a+') as f:
                f.truncate(len(data))
            self.hec_logger('Restored contents of the file', file_path=rclocal_path, orig_size=len(data),
                            dorked_size=offset)
            os.unlink(link_path)
            self.hec_logger('Removed hardlink', link_path=link_path)

    def run(self):
        self.start()
        try:
            self.do_run()
        except Exception as e:
            self.hec_logger('Uncaught exception within module, exiting module gracefully', error=str(e),
                            severity='error')
        self.finish()

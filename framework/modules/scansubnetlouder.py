try:
    from framework.main import ModuleBase, Utils
except ImportError:
    pass

class SubnetScanLouder(ModuleBase):
    @property
    def tags(self):
        return ['IntrusionSet3']

    @property
    def needs_root(self):
        return False

    @property
    def relative_delay(self):
        return 58

    @property
    def absolute_duration(self):
        return 25400

    def do_scan(self):
        import socket, random
        ports = [21,22,23,25,26,53,80,81,110,111,113,135,139,143,179,199,443,445,465,514,515,548,554,587,646,993,995,1025,
                 1026,1027,1433,1720,1723,2000,2001,3306,3389,5060,5666,5900,6001,8000,8008,8080,8443,8888,10000,32768,
                 49152,49154]
        timeout = 2  # time to wait on dropped packets
        for iface, net, sn, gw in Utils.routes():
            if gw == '0.0.0.0' and not net.startswith('169.'):
                self.hec_logger('Found local subnet', mask=sn, netaddr=net, ifname=iface)
                try:
                    hosts = list(Utils.subnet2list(net, sn))
                    self.hec_logger('Port scanning hosts in subnet', size=len(hosts), start=hosts[0], end=hosts[-1])
                    random.shuffle(hosts)
                    duration = timeout * len(hosts) * len(ports)
                    if duration > self.absolute_duration:
                        self.hec_logger('Apprx scan time longer than expected', severity='warning', duration=duration)
                    for host in hosts:
                        for port in ports:
                            s = socket.socket()
                            s.settimeout(timeout)
                            try:
                                s.connect((host, port))
                            except (socket.timeout, socket.error):
                                s.close()
                                continue
                            except Exception as e:
                                self.hec_logger(str(e), target=host, severity='error')
                                raise
                            else:
                                s.shutdown(socket.SHUT_RDWR)
                            s.close()
                except Exception as e:
                    self.hec_logger('Fatal socket error [{0}]'.format(e), severity='error')
                    break

    def do_run(self):
        pid = self.util_childproc(func=self.do_scan)
        self.util_orphanwait(pid)

    def run(self):
        self.start()
        try:
            self.do_run()
        except Exception as e:
            self.hec_logger('Uncaught exception within module, exiting module gracefully', error=str(e),
                            severity='error')
        self.finish()

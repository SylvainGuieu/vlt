from ..device import Device, cmd
class Shutter(Device):
    """
    shutter is a Device object and provide the additional
    following methods:
    cmdOpen: return the open command list
    cmdClose: return the close command list
    open: open the shutter  (e.i. 'ST T')
    close: close the shutter (e.i. 'ST F')
    """
    def _check(self):
        self._check_keys(["ST"])

    def cmd_open(self):
        return self['ST'].cmd(True)
    open_ = property(cmd_open)

    def cmd_close(self):
        return self['ST'].cmd(False)
    close_ = property(cmd_close)

    def open(self, timeout=None):
        return self.qsetup({"ST": True}, timeout=timeout)

    def close(self, timeout=None):
        return self.qsetup({"ST": False}, timeout=timeout)


class Shutters(list):
    def cmd_open(self):
        return cmd([shut.cmd_open() for shut in self])
    def cmd_close(self):
        return cmd([shut.cmd_close() for shut in self])

    def open(self, **kwargs):
        return self[0].proc.setup(function=self.cmd_open()+kwargs.pop("function",[]), **kwargs)

    def close(self, **kwargs):
        return self[0].proc.setup(function=self.cmd_close()+kwargs.pop("function",[]), **kwargs)

    def cmd(self, *args):
        if len(args)!=len(self):
            raise Exception("Expecting %d booleans"%(len(self)))
        return cmd([self[i].cmd(args[i]) for i  in range(len(self))])

    def setup(self, *args):
        return self[0].proc.msgSend("setup", dict(function=self.cmd(*args)))

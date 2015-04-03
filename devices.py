from vlt import Device, FunctionDict, DEFAULT_TIMEOUT, EmbigousKey


class Device(FunctionDict):
    """ Device object is actually a FunctionDict object with additional
    usefull methods dedicated to the device e.g. move, close, takeExposure,...
    """
    def __init__(self, fdict, statusKeys=None):
        FunctionDict.__init__(self, fdict)

        if statusKeys is not None:
            self.statusKeys = statusKeys
        self._check()

    def _check_keys(self, klist):
        """ check a list of keys, they must be in the dictionary and
        they must not be embigous
        """
        for k in klist:
            if k not in self:
                raise KeyError("Device '%s' Nead the key '%s' to work corectly" % (self.__class__.__name__, k))
            try:
                self[k]
            except EmbigousKey:
                raise KeyError("It seems that the needed key '%s' is not unique" % k)

    def _check(self):
        """ Function to check if all the functionality are here
        for a normal behavior.
        """
        pass

class Shuter(Device):
    """
    shuter is a Device object and provide the additional
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


class Shuters(list):
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


class Motor(Device):
    """ Motor is a device with the following additional methods

    moveTo : move to one position
    moveBy : move by a relative number of encrel

    and their coresponding cmd method cmdMoveTo, cmdMoveBy, ...
    """
    def _check(self):
       self._check_keys(["NAME", "ENC", "ENCREL", "INIT", "STOP"])


    def cmd_moveTo(self,targetpos):
        if issubclass(type(targetpos), str):
            return self['NAME'].cmd(targetpos, context=self)
        return self['ENC'].cmd(targetpos, context=self)

    def cmd_moveBy(self,encrel):
        return self['ENCREL'].cmd(encrel, context=self)

    def moveTo(self, targetpos, proc=None):
        return self.getProc(proc).setup(function=self.cmd_moveTo(targetpos))

    def moveBy(self,encrel, proc=None):
        return self.getProc(proc).setup(function=self.cmd_moveBy(encrel))




class Detector(Device):
    """ Detector is a Device with the followin additional method:

    start : start an exposure
    wait  : wait for the exposure to end
    abord  : abord the curent exposure
    takeExposure : setup the detector take the exposure and wait
    """
    functions = FunctionDict({})

    def start(self, expoId=None, detId=None,  at=None, timeout=None):
        return self.getProc().msgSend("start",
                                 dict(expoId=expoId, detId=detId,  at=at),
                                 timeout=timeout
                                 )

    def wait(self, expoId=None,  detId=None,  first=None,  all=None,
             cond=None, header=None, detlist=None, mode=None, timeout=None):
        return self.getProc().msgSend("wait",
                                 dict(expoId=expoId,  detId=detId,
                                      irst=first, all=all, cond=cond,
                                      header=header,
                                      detlist=detlist,
                                      mode=mode),
                                 timeout=timeout
                                 )

    def takeExposure(self, kwargs=None, expoId=0, timeout=None):
        kwargs = kwargs or {}
        expoId = self.setup(kwargs, expoId=expoId, timeout=timeout)
        self.start(expoId=expoId)
        self.wait(expoId=expoId)

    def takeExposureSeq( self, *args, **kwargs):
        return Sequence( (self.takeExposure , args, kwargs), modulo=True ).go()

    def abort(self):
        return self.proc.msgSend("ABORT")

    def cmd_subwins( self, coordinates, width=1, height=1, ref='ABSOLUTE'):
        l = len(coordinates)
        if not hasattr( width , "__iter__"): width=[width ]*l
        if not hasattr( height, "__iter__"): height=[height]*l
        cmd = self["SUBWINS"].getCmd(value=l)
        cmd += self["SUBWIN COORDINATES"].getCmd(value=ref)

        for i,(x,y),w,h in zip(range(1,l+1), coordinates, width, height):
            sv = "{w}x{h}+{x}+{y}".format(x=x,y=y,w=w,h=h)
            cmd += self["SUBWINi GEOMETRY"][i].getCmd(value=sv)
        return cmd

    def subwins(self,  coordinates, width=1, height=1, ref='ABSOLUTE'):
        return self.proc.setup(function=self.cmd_subwins(coordinates, width, height, ref=ref))

from ..device import Device, cmd
from ..sequence import sequence

class Detector(Device):
    """ Detector is a Device with the followin additional method:

    start : start an exposure
    wait  : wait for the exposure to end
    abord  : abord the curent exposure
    takeExposure : setup the detector take the exposure and wait
    """

    def start(self, expoId=None, detId=None,  at=None, timeout=None):
        """

        """
        return self.getProc().msgSend("start",
                                 dict(expoId=expoId, detId=detId,  at=at),
                                 timeout=timeout
                                 )

    def wait(self, timeout=None, **kwargs):
        """ run the command wait
        .proc.help("wait") for more info
        """
        return self.getProc().msgSend("wait",
                                 kwargs,
                                 timeout=timeout
                                 )

    def takeExposure(self, _kwargs_=None,
                     _include_= ["MODE", "IMGNAME"],
                     expoId=0, timeout=None,
                     **morekw):
        """
        takeExposure({"KEY1":val1}, KEY2=val2, expoId=0, timeout=1000 )
        Setup the instrument if any keywords are provided, start the exposure
        and wait for reult.
        The expoId is returned.
        """
        kwargs = _kwargs_ or {}
        kwargs.update(morekw)
        if len(kwargs):
            expoId = self.qsetup(kwargs,_include_=_include_,
                                expoId=expoId, timeout=timeout)
        self.start(expoId=expoId)
        self.wait(expoId=expoId)
        return expoId

    def takeExposureSeq(self, *args, **kwargs):
        """
        Same as takeExposure but run it in a sequence, one after the other
        where all individual argument are taken from list.
        The size of the repeat sequence is set by the bigest list, all other
        smaller list arguments are cycled.

        Example:
        det.takeExposure(dit=0.0  , ndit=1000, type="BIAS")
        det.takeExposure(dit=0.001, ndit=1000, type="DARK")
        det.takeExposure(dit=0.0  , ndit=1000, type="BIAS")
        det.takeExposure(dit=0.002, ndit=1000, type="DARK")


        Is equivalent to:
        det.takeExposureSeq(dit=[0.0, 0.001, 0.0, 0.002],
                            ndit=1000
                            type=["BIAS", "DARK"]
                           )

        see also:
            sequence
        """
        return sequence(self.takeExposure , *args, **kwargs).go()

    def abort(self, expoId=0, timeout=None):
        return self.proc.msgSend("ABORT", dict(expoId=expoId), timeout=timeout)

    def cmd_subwins( self, coordinates, width=1, height=1, ref='ABSOLUTE'):
        l = len(coordinates)
        if not hasattr(width , "__iter__"): width=[width ]*l
        if not hasattr(height, "__iter__"): height=[height]*l
        cmd = self["SUBWINS"].getCmd(value=l)
        cmd += self["SUBWIN COORDINATES"].getCmd(value=ref)

        for i,(x,y),w,h in zip(range(1,l+1), coordinates, width, height):
            sv = "{w}x{h}+{x}+{y}".format(x=x,y=y,w=w,h=h)
            cmd += self["SUBWINi GEOMETRY"][i].getCmd(value=sv)
        return cmd

    def subwins(self,  coordinates, width=1, height=1, ref='ABSOLUTE'):
        return self.proc.setup(function=self.cmd_subwins(coordinates, width, height, ref=ref))

""" Not functional yet """
def _updatedm(dm):
    dm.updateZernStatus()
    dm.updateActStatus()

class DM(Device):
    functions = None
    allfunctions = None
    xtilt = "ZERN3"
    ytilt = "ZERN2"
    setup_callback = None


    def __init__(self,proc, pref, functions):
        self.proc = proc
        self.functions = functions.restrict(pref)
        self.allfunctions = functions
        self.prefix = self.functions._prefix


        self.onSetup  = Actions(_updatedm)
        self.onUpdate = Actions()
        self.onUpdateZern = Actions()
        self.onUpdateAct  = Actions()

    def __getitem__(self, item):
        return self.functions[item]

    def update(self, *args, **kwargs):
        return self.functions.update(*args, **kwargs)

    def set(self, k,v):
        return self.functions.set(k,v)

    def cmdSetup(self, dictval=None, **kwargs):
        cmd = []
        if dictval:
            kwargs.update(dictval)

        for k,v in kwargs.iteritems():
            self.set(k,v)
            cmd += self.functions[k].getCmd()
        return cmd

    def cmdTmpSetup(self, dictval=None, **kwargs):
        cmd = []
        if dictval:
            kwargs.update(dictval)

        for k,v in kwargs.iteritems():
            cmd += self.functions[k].getCmd(v)
        return cmd


    def setup(self, dictval=None, **kwargs):
        out = self.proc.setup(self.cmdSetup(dictval,**kwargs))
        self.onSetup.run(self)
        return out

    def tmpSetup(self, dictval=None, **kwargs):
        out = self.proc.setup(self.cmdTmpSetup(dictval,**kwargs))
        self.onSetup.run(self)
        return out

    def cmdTiptilt(self, x, y):
        return self.cmdSetup( {self.xtilt:x, self.ytilt:y} )


    def getTiptilt(self):
        return (self.functions[self.xtilt].get(), self.functions[self.ytilt].get())
    def parseTiptilt(self, x, y):
         return  {self.xtilt:x , self.ytilt:y}
    def tiptilt(self,x,y):
        return self.setup(self.parseTiptilt(x,y))

    def setOffset(self):
        return self.tmpSetup( {"OFVO.CTRL":"SET"})

    def resetOffset(self):
        return self.tmpSetup( {"OFVO.CTRL":"SET"})

    def saveOffset(self, fileName=None):
        cmd =  {"OFVO.FILE":fileName} if fileName else {}
        cmd["OFVO.CTRL"] = "SAVE"
        return self.tmpSetup(cmd)

    def loadOffset(self, fileName=None):
        cmd =  {"OFVO.FILE":fileName} if fileName else {}
        cmd["OFVO.CTRL"] = "LOAD"
        return self.tmpSetup(cmd)

    def load(self, fileName, mode="modal"):
        if not mode in ["modal", "local"]:
            raise KeyError("mode should be 'modal' or 'local'")
        if mode=="local":
            return self.tmpSetup( {"ACT FILE":fileName} )
        else:
            return self.tmpSetup( {"ZERN FILE":fileName} )

    def save(self, fileName, mode="modal"):
        try:
            import pyfits as pf
        except:
            from astropy.io import fits as pf
        import numpy as np

        if not mode in ["modal", "local"]:
            raise KeyError("mode should be 'modal' or 'local'")
        if mode == "local":
            N = self.getNact()
            data = [self.functions["ACT%d"%i].get() for i in range(1, N+1)]
        elif mode == "modal":
            N = self.getNzern()
            data = [self.functions["ZERN%d"%i].get() for i in range(1, N+1)]
            f = pf.PrimaryHDU(np.array( data, dtype=np.float64))

        return f.writeto(fileName, clobber=True)



    def cmdZern(self, modes):
        return self.cmdSetup(self.parseZern(modes))



    def getZern(self, z):
        return self.functions[self.parseZernKey(z)]

    def getZerns(self, lst=None, update=False):
        if lst is None:
            lst = range(1,self.getNzern()+1)
        funcs = self.functions.restrict( self.parseZernKeys(lst))
        if update:
            funcs.statusUpdate(None)
        return funcs

    def parseZernKey(self, m):
        if isinstance(m,str):
            if m[0:4].upper() == "ZERN":
                m = int(m[4:None])
            elif m[0:1].upper() == "Z":
                m = int(m[1:None])
            else:
                raise KeyError("cannot understand zernic key '%s'"%m)
        return "ZERN%d"%m

    def parseZernKeys(self, keys):
        return  [self.parseZernKey(m) for m in keys]

    def parseZern(self, modes):
        it = modes.iteritems() if isinstance(modes,dict) else enumerate(modes,1)
        setout = {}
        for m,v in it:
            if isinstance(m,str):
                if m[0:4].upper() == "ZERN":
                     m = int(m[4:None])
                elif m[0:1].upper() == "Z":
                     m = int(m[1:None])
                else:
                     raise KeyError("cannot understand zernic key '%s'"%m)
            setout["ZERN%d"%m] = v
        return setout

    def zern(self, modes, mode=None):
        dzern  = self.parseZern(modes)
        if mode:
            dzern.setdefault("CTRL OP",mode)
        return self.setup(dzern)

    def getAct(self, a):
        return self.functions[self.parseActKey(a)]

    def getActs(self, lst=None, update=False):
        if lst is None:
            lst = range(1,self.getNact()+1)
        funcs = self.functions.restrict( self.parseActKeys(lst))
        if update:
            funcs.statusUpdate(None)
        return funcs

    def getZernValues(self, lst=None, update=False):
        return self.getZerns(lst, update).todict()
    def getActValues(self, lst=None, update=False):
        return self.getActs(lst, update).todict()


    def parseActKey(self, m):
        if isinstance(m,str):
            if m[0:3].upper() == "ACT":
                m = int(m[3:None])
            elif m[0:1].upper() == "A":
                m = int(m[1:None])
            else:
                raise KeyError("cannot understand actuator key '%s'"%m)
        return "ACT%d"%m

    def parseActKeys(self, acts):
        return [self.parseActKey(m) for m in acts]


    def parseAct(self, acts):

        it = acts.iteritems() if isinstance(acts,dict) else enumerate(acts,1)
        setout = {}
        for m,v in it:
            if isinstance(m,str):
                if m[0:3].upper() == "ACT":
                     m = int(m[3:None])
                elif m[0:1].upper() == "A":
                     m = int(m[1:None])
                else:
                     raise KeyError("cannot understand actuator key '%s'"%m)
            setout["ACT%d"%m] = v
        return setout
    def cmdAct(self, acts):
        return self.cmdSetup(self.parseAct(acts))

    def act(self, acts, mode=None):
        dact  = self.parseAct(acts)
        if mode:
            dact.setdefault("CTRL OP",mode)
        return self.setup(dact)

    def cmdReset(self):
        return self.cmdSetup(self.getReset())
    def getReset(self):
        return {"CTRL.OP":"RESET"}

    def reset(self):
        return self.setup(self.getReset())

    def getNact(self):
        return self.allfunctions["AOS.ACTS"].getOrUpdate(proc=self.proc)
    def getNzern(self):
        return self.allfunctions["AOS.ZERNS"].getOrUpdate(proc=self.proc)

    def status(self, statusItems=None):
        return self.functions.status(statusItems, proc=self.proc)

    def statusUpdate(self, statusItems=None):
        return self.functions.statusUpdate(statusItems, proc=self.proc)


    def getActStatus(self, nums=None, indict=None):
        return self.getIterableKeysStatus("ACT", nums or self.getNact(), indict=indict)

    def updateActStatus(self, nums=None, indict=None):
        out =  self.updateIterableKeysStatus("ACT", nums or self.getNact(), indict=indict)
        self.onUpdateAct.run(self)
        return out

    def updateZernStatus(self, nums=None, indict=None):
        out =  self.updateIterableKeysStatus("ZERN", nums or self.getNzern(), indict=indict)
        self.onUpdateZern.run(self)
        return out

    def getZernStatus(self, nums=None, indict=None):
        return self.getIterableKeysStatus("ZERN", nums or self.getNzern(), indict=indict)

    def updateAll(self):
        keys = ["%s%d"%("ZERN",i) for i in range(1,self.getNzern()+1)]+["%s%d"%("ACT",i) for i in range(1,self.getNact()+1)]
        self.functions.restrict(keys).statusUpdate(None)
        self.onUpdate.run(self)

    def updateIterableKeysStatus(self,key , nums, indict=None):
        if isinstance(nums, int):
            nums = range(1,nums+1)
            if indict is None:
                indict = True
        else:
            indict = False

        keys  = ["%s%d"%(key,i) for i in nums]
        frest = self.functions.restrict(keys)
        frest.statusUpdate(None)

        self.onUpdate.run(self)

        if indict:
            return {n:frest["%s%d"%(key,n)].get() for n in nums}
        else:
            return [frest["%s%d"%(key,n)].get() for n in nums]

    def getIterableKeysStatus(self,key , nums , indict=None):
        if isinstance(nums, int):
            nums = range(1,nums+1)
            if indict is None:
                indict = False
        else:
            indict = True

        keys = ["%s%d"%(key,i) for i in nums]
        vals = self.status(keys)

        pref = self.functions._prefix+"." if self.functions._prefix else ""
        if indict:
            return {n:vals[pref+"%s%d"%(key,n)] for n in nums}
        else:
            return [vals[pref+"%s%d"%(key,n)] for n in nums]

class DMs(list):
    def plot(self, axes=None, fig=None, vmin=None, vmax=None, cmap=None):
        if axes is None:
            if fig is not None:
                axes = fig.get_axes()
            else:
                if self[0].graph:
                    import math as m
                    N = len(self)
                    nx = int(m.sqrt(N))
                    ny = int(m.ceil(N/float(nx)))
                    fig = self[0].graph.plt.figure("actuactors")
                    fig.clear()
                    axes = [fig.add_subplot(nx,ny, i+1) for i in range(N)]
                    #fig, axes = self[0].graph.plt.subplots(nx,ny)
                    #axes = axes.flatten().tolist()
        if len(axes)<len(self):
            raise Exception("not enought axes to plot %d dm"%(len(self)))

        for i in range(len(self)):
            a  = axes[i]
            dm = self[i]
            dm.plot(axes=a, vmin=vmin, vmax=vmax, cmap=cmap )

    def plotzern(self, axes=None, fig=None, **kwargs):
        if axes is None:
            if fig is not None:
                axes = fig.get_axes()
            else:
                if self[0].zerngraph:
                    import math as m
                    N = len(self)
                    nx = int(m.sqrt(N))
                    ny = int(m.ceil(N/float(nx)))
                    fig = self[0].graph.plt.figure("zernics")
                    fig.clear()
                    axes = [fig.add_subplot(nx,ny, i+1) for i in range(N)]
                    #fig, axes = self[0].graph.plt.subplots(nx,ny)
                    #fig, axes = self[0].graph.plt.subplots(N)
                    #axes = axes.flatten().tolist()
                else:
                    raise Exception("no zeengraph set")
        if len(axes)<len(self):
            raise Exception("not enought axes to plot %d dm"%(len(self)))
        print kwargs
        for i in range(len(self)):
            a  = axes[i]
            dm = self[i]
            dm.plotzern(axes=a, **kwargs)



    def reset(self):
        for dm in self:
            dm.reset()

    def zern(self, modes):
        for dm in self:
            dm.zern(modes)
    def act(self, actvals):
        for dm in self:
            dm.act(actvals)


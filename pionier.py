from __future__ import print_function
from vlt import processClass, devices
from vlt.io import readDictionary

def log(*msg, **kwargs):
    print(*msg, **kwargs)
import os
import vlt
dpr_id = os.getenv("DPR_ID")
dpr_id = dpr_id or "PIONIER"

log( "opening new process pnoc ...",end=" ")
if dpr_id == "PIONIER":
    pnoc = vlt.openProcess("pnoControl")
elif dpr_id == "BETI":
    pnoc = vlt.openProcess("beoControl")

vlt.setDefaultProcess(pnoc)
log("ok")


####
# Load the functional dictionaries
#
log("Reading Dictionaries ...", end=" ")
if dpr_id == "PIONIER":
    log("ACS", end=" ")
    acs = readDictionary(dpr_id+"_ACS")
    aos = vlt.FunctionDict()
elif dpr_id == "BETI":
    log("AOS", end=" ")
    aos = readDictionary(dpr_id+"_AOS")
    acs = vlt.FunctionDict()

log("CFG", end=" ")
cfg = readDictionary(dpr_id+"_CFG")
log("DCS", end=" ")
dcs = readDictionary(dpr_id+"_DCS")
log("ICS", end=" ")
ics = readDictionary(dpr_id+"_ICS")
log("OS", end=" ")
os = readDictionary(dpr_id+"_OS")
log("DPR", end=" ")
dpr = readDictionary("DPR")
log("OSB", end=" ")
osb = readDictionary("OSB")
log(" => allf")
allf = acs + aos + cfg + dcs + ics + os + dpr + osb

####
# Add the 4 shuters
shutters = devices.Shutters([devices.Shutter(ics.restrict("INS.SHUT%d"%i),
                                  statusItems=[""]) for i in range(1, 5)])
shut1, shut2, shut3, shut4 = shutters

####
# dispersion motor
disp = devices.Motor(ics.restrict("INS.OPTI3"), statusItems=[""])

####
# Detector
# needs the DET. keywords plus some extras
class PionierDetector(devices.Detector):
    def statusUpdate(self, statusItems=None, proc=None):
        super(PionierDetector, self).statusUpdate()
        if statusItems is None:
            statusItems = self.statusItems

        if "SUBWINS" in statusItems and self["SUBWINS"].hasValue():
            subs_status = []
            for i in range(1, self["SUBWINS"].getValue()+1):
                subs_status.expend(
                    self.restrict("SUBWIN%d"%i).msgs()
                )
            if len(subs_status):
                self.statusUpdate(subs_status)




det = PionierDetector(
                       dcs.restrict("DET")+
                       dpr+
                       osb.restrict("OCS.DET")+
                       ics.restrict([("INS.MODE", "MODE")]),
                       statusItems=["DIT", "NDIT", "POLAR", "SUBWINS"]
                       )
##
# To remove some keyword embiguities
det["TYPE"] = det["DPR.TYPE"]
# set the default mode to ENGINEERING
det["mode"] = "ENGINEERING"
det["imgname"] = dpr_id+"_"











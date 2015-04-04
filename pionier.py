from __future__ import print_function
from vlt import processClass, devices, readDictionary, EmbigousKey


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

log("Reading Dictionaries ...", end=" ")
log("ACS",end=" ")
acs = readDictionary(dpr_id"_ACS")
log( "CFG",end=" ")
cfg = readDictionary(dpr_id"_CFG")
log( "DCS",end=" ")
dcs = readDictionary(dpr_id"_DCS")
log( "ICS",end=" ")
ics = readDictionary(dpr_id"_ICS")
log( "OS",end=" ")
os  = readDictionary(dpr_id"_OS")
log( "DPR",end=" ")
dpr = readDictionary("DPR")
log( "OSB",end=" ")
osb = readDictionary("DPR")
log( " => allf")
allf = acs + cfg + dcs + ics + os + dpr + osb







from __future__ import print_function
from vlt import processClass, devices, readDictionary, EmbigousKey


def log(*msg, **kwargs):
    print(*msg, **kwargs)

import vlt

log( "opening new process pnoc ...",end=" ")
pnoc = vlt.openProcess("pnoControl")
vlt.setDefaultProcess(pnoc)
log( "ok")

log( "Reading Dictionaries ...",end=" ")
log( "ACS",end=" ")
acs = readDictionary("PIONIER_ACS")
log( "CFG",end=" ")
cfg = readDictionary("PIONIER_CFG")
log( "DCS",end=" ")
dcs = readDictionary("PIONIER_DCS")
log( "ICS",end=" ")
ics = readDictionary("PIONIER_ICS")
log( "OS",end=" ")
os  = readDictionary("PIONIER_OS")
log( "DPR",end=" ")
dpr = readDictionary("DPR")
log( "OSB",end=" ")
osb = readDictionary("DPR")
log( " => allf")
allf = acs + cfg + dcs + ics + os + dpr + osb







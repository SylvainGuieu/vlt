import vlt
d = vlt.readDictionary("PIONIER_ICS")
d["INS.TEMP1.VAL"] = 1.0;
d["INS.TEMP2.VAL"] = 10.0

print d.restrictValue([1, 10])
print d.restrictValue(lambda v: v>1.0)


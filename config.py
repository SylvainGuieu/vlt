"""
Configuration file of the vlt package. to be changed with cautions
"""
import os


INTROOT  = os.getenv("INTROOT") or ""
INS_ROOT = os.getenv("INS_ROOT") or ""
INSROOT  = INS_ROOT
VLTROOT  = os.getenv("VLTROOT") or ""
DPR_ID   = os.getenv("DPR_ID") or ""
VLTDATA  = os.getenv("VLTDATA") or ""


config = {
    # list of directories/prefix/sufix/extention for the CDT files
    "cdt":{
        ## List of path from where to find cdt files
        "path": [os.path.join(INTROOT, "CDT"),
                 os.path.join(VLTROOT, "CDT")],
        "prefix":"",        
        "extention":"cdt", 
        # list of directory where cdt temporaly py file will be
        # created
        "pydir":os.path.join(os.path.dirname(__file__), "processes"), 
        #  boolean value for cdt debug
        "debug":False
    }, 

    "dictionary": {
        # list of directories containing the dictionary files
        "path": [os.path.join(INS_ROOT, "SYSTEM/Dictionary"),
                 os.path.join(VLTROOT, "config")],
        # dictionary file prefix         
        "prefix" : "ESO-VLT-DIC.",
        "extention" : ""          
    }, 
        
 
    "tsf":{
        "path": [os.path.join(INS_ROOT, "SYSTEM/COMMON/TEMPLATES/TSF")], 
        "extention":"tsf", 
        "prefix":""
    },
    "isffile": os.path.join(INS_ROOT, "SYSTEM/COMMON/CONFIGFILES/PIONIER.isf"),

    "obd":{
        ## add :: for recursive directories 
        "path": [os.path.join(INS_ROOT, "SYSTEM/COMMON/TEMPLATES/OBD")], 
        "extention":"obd", 
        "prefix":""            
    },
    # if key_match_case is true, the Function anf FunctionDict objects
    # becomes case sensitive meaning that, e.g, dcs["DIT"] != dcs["dit"]
    # default is false
    "key_match_case": False,
    #
    # The system command for msgSend    
    "msgSend_cmd": "msgSend",
    # a default timeout for msgSend commands, leave it None for
    # no default
    "timeout": None,
    # in debug mode msgSend are not sent
    "debug": False,
    # verbose level
    "verbose": 1
}

# debug local configuration
# config["cdtpath"] += ["/Users/guieu/python/vlt/CDT"]
# config["dictionarypath"] += ["/Users/guieu/python/vlt/Dictionary",
#                             "/Users/guieu/python/vlt/Dictionary/CCSLite"
#        ]
config["debug"] = not os.getenv("HOST")  in ["wbeti" , "wpnr" , "wbeaos"]


import re
import pandas as pd
import datetime
import time

class LogFile(file):
    data = {}
    linereg = re.compile("([a-zA-Z]+) +([0-9]+) +([0-9:]+) +([^ ]+) +([^ ]+) +([^ ]+) +([0-9:]+)> ([^/=]+) = ([^/]*) / +(.+)$")    
    keys    = ["month", "day", "time", "host", "who", "env", "time2", "key", "val", "comment"]
    time_resolution = 1
    dumpfile = None
    date = None
    before = None
    after  = None
    def info2date(self, info):
        t = datetime.datetime.strptime(info['time'], "%H:%M:%S")
        if self.time_resolution>1:
            t = roundTime(t, self.time_resolution)
        month = datetime.datetime.strptime(info['month'], "%b").month # convert month to numeric value
        return t.replace( year=2014, month=month, day=int(info['day']) )
        
    firstLine = True    
    date = None
    def __init__(self, *args, **kwargs): 
        #self.data = pd.DataFrame()
        self.definition = kwargs.pop("definition", None)
        self.data   =  {}
        self.lastdata = {}
        self.lastdate = None
        self.keyset = set()
        super(LogFile,self).__init__(*args, **kwargs)
        
    def parseLine(self, line):
        m = self.linereg.match( line)
        if m:
            info = dict( zip( self.keys, m.groups()))
            
            date = self.info2date(info)
            
            if info["key"]=="DATE":                     
                try:
                    date = datetime.datetime.strptime( info["val"], "%Y-%m-%dT%H:%M:%S.%f" )
                    self.date = date
                except:
                    pass
            if self.before and date>self.before: return 
            if self.after  and date<self.after : return 

            self.firstLine = False   
            #date = "{month}-{day}-{time}".format(**info)
            
            key = info["key"]
            val = info["val"]
            if self.definition is not None:
                if not key in self.definition:
                    return None
                definition = self.definition[key]
                if "name" in definition:
                    key = definition["name"]
                if "dtype" in definition:
                    val = definition["dtype"](val)
            
            if not date in self.data:
                self.data[date] = {}
            self.data[date][key] = val
            self.lastdata[key]   = val
            self.lastdate = date
            if self.dumpfile:
                self.dumpfile.write(line)
            #self.data.set_value(date, key, val)
    
    def parse(self, time_resolution=None, before=None, after=None):
        if time_resolution: self.time_resolution = time_resolution
        if before: self.before=before
        if after : self.after = after
        line = self.readline()
        while len(line):            
            self.parseLine(line)
            line = self.readline()
        return self.data
    
    def to_df( self, keys=[]):
        return pd.DataFrame( self.data.values(), self.data.keys())
        
    def to_array(self, keys=["mjd"], dtype=float, fillvalue=-9.99, allkeys=False):
        import numpy as np
        fillvalue = dtype(fillvalue)
        
        shape = ( len(self.data), len(keys) )
        dtypes = [ (k,dtype) for k in keys]
        #A = np.ndarray( shape, dtype=dtype)
        A = np.ndarray( len(self.data) , dtype=dtypes)
        mask = np.ndarray( (len(self.data),), dtype=bool)
        mask[:] = True
        i=0 
        j=0 
        for date,dv in self.data.iteritems():
            vl = []
            for k in keys:
                if k=="mjd":
                    v = time.mktime(date.timetuple())-time.timezone
                else:
                    if  k in dv:
                        v = dv[k]
                    else:
                        v = fillvalue
                        mask[i] = False
                vl.append(v)
                #A[i,j] = v
                j +=1
            A[i] = tuple(vl)

            j =  0 
            i += 1
        if allkeys:
            A = A[mask]
        if "mjd" in keys:
            A.sort(order="mjd")
        
        return A


class OpsLogFile(LogFile):
     linereg = re.compile("^[^>]*([0-9][0-9][:][0-9][0-9][:][0-9][0-9])> ([^/=]+) = ([^/]*) / +(.+)$")
     keys  = ["time", "key", "val", "comment"]
     date  = datetime.datetime(2014, 01,01)
     year  = 2014
     month = 01
     day   = 01
     def info2date(self, info):      
         

        t = datetime.datetime.strptime(info['time'], "%H:%M:%S")
        if self.time_resolution>1:
            t = roundTime(t, self.time_resolution)
        
        if self.date:
            return t.replace( year=self.date.year, month=self.date.month, day=self.date.day)
        return t.replace( year=self.year, month=self.month, day=self.day)
             



def readSensors(filename):    
    definition = { "INS SENS%d STAT"%i:{"name":"S%d"%i,"dtype":float} for i in range(1,16)}
    f = LogFile(filename, definition=definition)
    f.parse()
    return f


# temp = (S6 - 1080+ (-1.71)*66.93)/-1.71



###############################################################################
#
#  Time Conversions
#
################################################################################
import math, sys, string



def gd2jd(year, month, day, hh, min, sec):
    UT = hh+min/60. +sec /3600.
    
#    Formula for Conversion:
#
# JD =367K - <(7(K+<(M+9)/12>))/4> + <(275M)/9> + I + 1721013.5 + UT/24 
# - 0.5sign(100K+M-190002.5) + 0.5
#where K is the year (1801 <= K <= 2099), M is the month (1 <= M <= 12), I is the day of the month (1 <= I <= 31), and UT is the universal time in hours ("<=" means "less than or equal to"). The last two terms in the formula add up to zero for all dates after 1900 February 28, so these two terms can be omitted for subsequent dates. This formula makes use of the sign and truncation functions described below:
#
#The sign function serves to extract the algebraic sign from a number.
#Examples: sign(247) = 1; sign(-6.28) = -1.
#
#The truncation function < > extracts the integral part of a number.
#Examples: <17.835> = 17; <-3.14> = -3.
#
#The formula given above was taken from the 1990 edition of the U.S. Naval Observatory's Almanac for Computers (discontinued).
#
#Example: Compute the JD corresponding to 1877 August 11, 7h30m UT.
#Substituting K = 1877, M = 8, I = 11 and UT = 7.5,
#JD = 688859 - 3286 + 244 + 11 + 1721013.5 + 0.3125 + 0.5 + 0.5
#= 2406842.8125
    

    JD = 367*year - int((7*(year+ int((month+9)/12.)))/4.) + int((275*month)/9.) + day + 1721013.5 + UT/24. - 0.5*math.copysign(1,100*year+month-190002.5) + 0.5
    return JD

def gd2mjd( year, month, day, hh, min, sec):
    # see http://tycho.usno.navy.mil/mjd.html
    return gd2jd( year, month, day, hh, min, sec) - 2400000.5

def date2jd(date):
    return gd2jd( date.year, 
                  date.month, 
                  date.day, 
                  date.hour, 
                  date.minute, 
                  date.second+date.microsecond*1e-6
    )

def date2mjd(date):
    return date2jd(date) - 2400000.5

def jd2gd(jd):
    jd=jd+0.5
    Z=int(jd)
    F=jd-Z
    alpha=int((Z-1867216.25)/36524.25)
    A=Z + 1 + alpha - int(alpha/4)

    B = A + 1524
    C = int( (B-122.1)/365.25)
    D = int( 365.25*C )
    E = int( (B-D)/30.6001 )

    dd = B - D - int(30.6001*E) + F

    if E<13.5:
        mm=E-1

    if E>13.5:
        mm=E-13

    if mm>2.5:
        yyyy=C-4716

    if mm<2.5:
        yyyy=C-4715
    
    h=int((dd-int(dd))*24)
    min=int((((dd-int(dd))*24)-h)*60)
    sec=86400*(dd-int(dd))-h*3600-min*60
    
    return ( int(yyyy), int(mm), int(dd), int(h), int(min), sec)

def mjd2gd(jd):
    return jd2gd( jd + 2400000.5  )


def jd2date(jd):
    d = list(jd2gd(jd))
    sec = d[-1]
    #convert the fractional seconds to integer second and microsecond 
    d[-1] = int(sec)
    microsec = int( (sec-d[-1]) * 1e6)
    
    d.append(microsec)    
    return datetime.datetime(*d)
def mjd2date(jd):
    return jd2date( jd + 2400000.5  )  

def roundTime(dt, roundTo=60):
   """Round a datetime object to any time laps in seconds
   dt : datetime.datetime object, default now.
   roundTo : Closest number of seconds to round to, default 1 minute.
   Author: Thierry Husson 2012 - Use it as you want but don't blame me.
   """
   seconds = (dt - dt.min).seconds
   # // is a floor division, not a comment on following line:
   rounding = (seconds+roundTo/2) // roundTo * roundTo
   return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)






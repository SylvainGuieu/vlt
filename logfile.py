import re
import pandas as pd
import datetime
import time
import os

from inspect import getargspec

def _issignature(want,signature):
    return signature == want

def _getsignature(method):
    spec = getargspec(method)
    # nargs = nargs-1 if method is bounded
    return len(spec.args) - (hasattr(method, "__self__") and
                            (method.im_self is not None))

def _call_decorator_parser(signature, method):
    if signature == 1:
        def tmp(date, key, value):
            return method(value)
        return tmp
    if signature == 2:
        def tmp(date, key, value):
            return method(key, value)
        return tmp
    if signature == 3:
        def tmp(date, key, value):
            return method(date, key, value)
        return tmp
    if signature == 4:
        def tmp(info, date, key, value):
            return method(date, key, value)
        return tmp
    raise Exception("Signature function must be (value) or (key,value) or (date,key,value) (infodict, date, key, value)")

def _call_decorator_matcher(signature, method):
    if signature == 1:
        def tmp(date, key, value):
            return method(key)
        return tmp
    if signature == 2:
        def tmp(date, key, value):
            return method(key, value)
        return tmp
    if signature == 3:
        def tmp(date, key, value):
            return method(date, key, value)
        return tmp
    raise Exception("Signature function must be (key) or (key,value) or (date,key,value)")


reg_date_file =  re.compile("^.*([0-9][0-9][0-9][0-9])-([0-9][0-9])-([0-9][0-9]).*$")

def _true(date, key, val):
    return True

def guesstype(val):
    try:
        return int(val)
    except:
        try:
            return float(val)
        except:
            return val


class LogFile(file):
    data = {}
    linereg = re.compile("([a-zA-Z]+) +([0-9]+) +([0-9:]+) +([^ ]+) +([^ ]+) +([^ ]+) +([0-9:]+)> ([^/=]+) = ([^/]*) / +(.+)$")
    keys    = ["month", "day", "time", "host", "who", "env", "time2", "key", "val", "comment"]
    time_resolution = 1
    dumpfile = None
    date = None
    before = None
    after  = None
    _callparse = None
    _callmatch = None
    #fparse = None
    fmatch = None

    def fparse(self, key, val):
        print key, val, type(self.guesstype(val))
        return self.guesstype(val)

    def info2date(self, info):
        """extract from a parsed line (the info dictionary) the date(/time)
        object.
        """
        t = datetime.datetime.strptime(info['time'], "%H:%M:%S")
        if self.time_resolution>1:
            t = roundTime(t, self.time_resolution)
        # convert month to numeric value
        if "month" in info:
            month = datetime.datetime.strptime(info['month'], "%b").month
        else:
            month = self._month
        return t.replace(year=int(info.get("year", self._year)), month=month,
                         day =int(info.get('day', self._day)))

    firstLine = True
    date = None
    def __init__(self, *args, **kwargs):
        """ Open a logfile reader
        same arguments than file plus:

        Keywords [all these keywords are also valid in the parse function]
        --------
          - year: the default year for date
          - month: the default month (numerical)
          - day:  the default day
              These keywords are usefull only if the data cannot be read from the
              log file. If omited guess the date from the filename or the creation
              date.

          - fmatch: a function of signature (key) or (key,val) or (date, key,val)
                    must return a boolean.
                    if fmatch(key) is True fparse(val) is executed (see below)

          - fparse: a function of signature (val) or (key,val) or (date,key,val)
                    must return anything that will be stored in the data.
                    if return is None the value will be ignored

                if fmatch *is* None and fparse *is not* None:
                    fparse is called for each lines
                if fmatch *is not* None and fparse *is* None:
                    the value is stored in data only if the result of
                    fmatch is True.



                One can use this function to parse type, to plot, to print lines etc...
              example:
                f = LogFile("/vltdata/tmp/logFile")
                f.parse( fmatch = lambda key: "SENS" in key, fparse = lambda val: float(val))
                 -or-
                f.parse( fparse=f.gesstype )



        definition  = a dictionary with keywords definition.
        """
        #self.data = pd.DataFrame()
        lt = time.localtime()

        kwdate = {k:kwargs.pop(k) for k in ["year","month","day"] if k in kwargs}
        self.definition = kwargs.pop("definition", None)

        self.fparse = kwargs.pop("fparse", self.fparse)
        self.fmatch = kwargs.pop("fmatch", _true if self.fparse is not None else self.fmatch)


        self.data = {}
        self.lastdata = {}
        self.lastdate = None
        self.keyset = set()
        super(LogFile,self).__init__(*args, **kwargs)

        year, month, day = filepath2date(self.name)
        self._year = kwdate.pop("year", None) or year
        self._month = kwdate.pop("month", None) or month
        self._day = kwdate.pop("day", None) or day


    guesstype = staticmethod(guesstype)

    def parseLine(self, line):
        m = self.linereg.match( line)
        if m:
            info = dict( zip( self.keys, m.groups()))

            date = self.info2date(info)

            if info["key"]=="DATE":
                try:
                    date = datetime.datetime.strptime(info["val"], "%Y-%m-%dT%H:%M:%S.%f" )
                    self.date = date
                except:
                    pass
            if self.before and date>self.before: return
            if self.after  and date<self.after : return

            self.firstLine = False
            #date = "{month}-{day}-{time}".format(**info)

            key = info["key"]
            val = info["val"]

            if self._callmatch:
                test = self._callmatch(date, key, val)
                if test and self._callparse:
                    val = self._callparse(date, key, val)
                elif not test and not self._callparse:
                    val = None


            elif self.definition is not None:
                if not key in self.definition:
                    return None
                definition = self.definition[key]
                if "name" in definition:
                    key = definition["name"]
                if "dtype" in definition:
                    val = definition["dtype"](val)

            if val is None:
                return

            if not date in self.data:
                self.data[date] = {}
            self.data[date][key] = val
            self.lastdata[key]   = val
            self.lastdate = date
            if self.dumpfile:
                self.dumpfile.write(line)
            #self.data.set_value(date, key, val)

    def parse(self, time_resolution=None, before=None, after=None,
              fmatch=None, fparse=None, year=None, month=None, day=None
              ):
        if time_resolution: self.time_resolution = time_resolution
        if before: self.before= before
        if after : self.after = after
        if year  : self._year = int(year)
        if month : self._month= int(month)
        if day   : self._day = int(day)

        if fparse: self.fparse= fparse
        if fmatch: self.fmatch = fmatch


        if self.fparse and self.fmatch is None:
            self.fmatch = _true

        if self.fparse:
            self._callparse = _call_decorator_parser(_getsignature(self.fparse), self.fparse)
        if self.fmatch:
            self._callmatch = _call_decorator_matcher(_getsignature(self.fmatch), self.fmatch)


        line = self.readline()
        while len(line):
            self.parseLine(line)
            line = self.readline()
        return self.data

    def to_df(self, keys=[]):
        return pd.DataFrame( self.data.values(), self.data.keys())

    def to_array(self, keys=["mjd"], dtype=float, fillvalue=-9.99,
                 allkeys=False):
        import numpy as np
        fillvalue = dtype(fillvalue)

        shape = ( len(self.data), len(keys) )
        dtypes = [ (k,dtype) for k in keys]
        #A = np.ndarray( shape, dtype=dtype)
        A = np.ndarray(len(self.data), dtype=dtypes)
        mask = np.ndarray((len(self.data),), dtype=bool)
        mask[:] = True
        i=0
        j=0
        for date, dv in self.data.iteritems():
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

#     date  = datetime.datetime(2014, 01,01)
#     year  = 2014
#     month = 01
#     day   = 01
#     def info2date(self, info):
#
#
#        t = datetime.datetime.strptime(info['time'], "%H:%M:%S")
#        if self.time_resolution>1:
#            t = roundTime(t, self.time_resolution)
#
#        if self.date:
#            return t.replace( year=self.date.year, month=self.date.month, day=self.date.day)
#        return t.replace( year=self.year, month=self.month, day=self.day)


def filepath2date(path):
    """ try to guess year, month, day from a file name """
    name = os.path.split(path)[1]
    m = reg_date_file.match(name)
    if not m:
        try:
            lt = time.localtime(os.path.getctime(path))
        except:
            lt = time.localtime()
        return lt.tm_year, lt.tm_mon, lt.tm_mday

    return tuple( int(g) for g in m.groups() )


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






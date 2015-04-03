#from vlt import vltdb as db
import vltdb as db
# LOGICAL value = 1 
# INT32/UINT32 value = 0 
# BYTES value =  
# DOUBLE value = 260 
# DOUBLE value = 95 
# DOUBLE value = 288 
# DOUBLE value = 97 
# BYTES value = blue 
# BYTES value =  
# BYTES value =  
# INT32/UINT32 value = 2 
# DOUBLE value = 0 

class rect(object):
    datapos = {"vis":0 , "x0":3, "y0":4, "x1":5, "y1":6, "color":7, "width":10}
    addrs = ["graph"]
    this = "rect"
    def __init__(self, name, rectNumbers=None):
        self.db = db.db(name)
        if rectNumbers is None:
            rectNumbers = self.db.read(self.addrs, self.this+".maxNumElem")
            if not len(rectNumbers):
                raise ValueError("Cannot read the maximum number of element on the data base")
            rectNumbers = range(int(rectNumbers[0]))
        
        self.rectNumbers = list(rectNumbers)
        self.index = 0
    
    def read(self, index):
        return self.db.read( self.addrs , self.this+".itemConfig({0:d})".format(index))

    def write(self, index, vals):
        return self.db.writeList( self.addrs,self.this+".itemConfig", index, vals)
    
    def writeDict(self, index, vals):
        return self.db.writeDict( self.addrs,self.this+".itemConfig", index, vals)
    
    def show(self, show=True):
        return self.db.write(self.addrs, self.this+".showGroup", int(show))
        
    def redraw( self ):
        return self.db.write(self.addrs, self.this+".drawGraphics", self.this)
        
    def add(self, x0, y0, width, height, color="green"):
        x1 = x0 + width
        y1 = y0 + height
        if self.index>=len(self.rectNumbers):
            raise Exception("Exceeded the number of rectangle allowed")
        self.write( self.rectNumbers[self.index] ,[True,0,"",x0,y0,x1,y1,color, "", "", 2, 0])    
        self.index += 1
    
    def change( self, index, **kwargs):
        
        vals = {}
        for k,v in kwargs.iteritems():
            if not k in self.datapos:
                raise KeyError("unknown param '%s'"%k)
            vals[self.datapos[k]] = v
        self.writeDict(index, vals)
        
    def shift( self, index, xshift=0, yshift=0):
        vals = self.read(index)
        x0 = vals[self.datapos["x0"]]
        y0 = vals[self.datapos["y0"]]
        x1 = vals[self.datapos["x1"]]
        y1 = vals[self.datapos["y1"]]
        return self.change(index, x0=x0+xshift, x1=x1+xshift, y0=y0+yshift, y1=y1+yshift)
    
    def shiftAll( self, xshift=0, yshift=0):
        for i in self.rectNumbers:
            self.shift(i, xshift, yshift)
            
    def clear(self):
        for i in self.rectNumbers:
            self.write(i, [False,0,"",0 , 0,0,0,"white", "", "", 1, 0] )
        self.index = 0

    
    def fromRectangles(self, rect, xmargin=0, ymargin=0, **kwargs):
        """
        change the dadabase values according to the list of rectanges as defined in mathplotlib:
           [  [ (x0,y0), width, hwight], ... ]
        """
        kwargs.setdefault("vis",1)
        kwargs.setdefault("color", "green")
        kwargs.setdefault("width",2)
        
        for i,r in enumerate(rect):
            x0 = r[0][0]
            x1 = x0+r[1]+xmargin
            y0 = r[0][1]
            y1 = y0+r[2]+ymargin            
            self.change(self.rectNumbers[i], x0=x0, y0=y0, x1=x1, y1=y1, **kwargs)
        
        
        
        
        

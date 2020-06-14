# -*- coding, utf-8 -*-
"""
Created on Mon Jan 28 14,25,14 2019

@author, AsteriskAmpersand
"""
from collections import OrderedDict
import struct
try:
    from ..common import Cstruct as CS
except:
    import sys
    sys.path.insert(0, r'..\common')
    import Cstruct as CS

class Mod3HeaderBoundaries(CS.PyCStruct):
    fields = OrderedDict([
            ("center","float[3]"),
            ("radius","float"),
            ("minBox","float[4]"),
            ("maxBox","float[4]")            
            ])

class Mod3HeaderFloatSegment(CS.PyCStruct):
    fields = OrderedDict([
            ("editorClippingDistance","float"),
            ("unknSegmentStart","short[2]"),#01 00, 05 00
            ("unknData","float[8]"),# [0,1,1,1, 1,1,1,1]
            ("unknData2","float[8]"),# [0,1,1,1, 1,1,1,1]
            ("unknSegmentContinue","int"),# 1
            ("lodDistances","float[5]")#360 60 20 10 10
            ])
    
class Mod3HeaderByteSegment(CS.PyCStruct):
    fields = OrderedDict([
            ("unkn1","byte[64]")         
            ])

class MOD3Header(CS.PyCStruct):
    fields = OrderedDict([
            ("id","long"),
            ("version","ubyte"),
            ("version2","ubyte"),
            ("boneCount","short"),
            ("meshCount","short"),
            ("materialCount","short"),
            ("vertexCount","long"),
            ("faceCount","long"),
            ("vertexIds","long"),#num_edges
            ("vertexBufferSize","long"),
            ("secondBufferSize","long"),
            ("groupCount","uint64"),
            ("creationDate","uint64"),
            ("boneOffset","uint64"),
            ("groupOffset","uint64"),
            ("materialNamesOffset","uint64"),
            ("meshOffset","uint64"),
            ("vertexOffset","uint64"),
            ("facesOffset","uint64"),
            ("trailOffset","uint64"),
            ("unkOffset2","uint64"),
            ])
    def __init__(self):
        super().__init__()
        self.Boundaries = Mod3HeaderBoundaries()
        self.FloatSegment = Mod3HeaderFloatSegment()
        self.ByteSegment = Mod3HeaderByteSegment()
    def marshall(self,data):
        super().marshall(data)
        self.Boundaries.marshall(data)
        self.FloatSegment.marshall(data)
        self.ByteSegment.marshall(data)
    def construct(self,data):
        super().construct(data)
        self.Boundaries.construct(data["boundingData"])
        self.FloatSegment.construct(data["floatData"])
        self.ByteSegment.construct(data["byteData"])
    scenePropertyList = ["vertexIds", "groupCount", "materialCount"]
    defaultProperties = {"id":0x444F4D,"version":237,"version2":0,"secondBufferSize":0,"unkOffset2":0}
    requiredProperties = set(scenePropertyList)
    def sceneProperties(self):
        return {**{prop:self.__getattribute__(prop)
                for prop in self.scenePropertyList},
                **{"ByteSegment:%s"%prop:getattr(self.ByteSegment,prop) for prop in self.ByteSegment.fields},
                **{"FloatSegment:%s"%prop:getattr(self.FloatSegment,prop) for prop in self.FloatSegment.fields}}    
        
class Mod3Material(CS.PyCStruct):
    buffersize = 128
    fields = OrderedDict([
            ("materialName","char[128]")
            ])
    requiredProperties = {"materialName"}
        
class Mod3Materials(CS.Mod3Container):
    def __init__(self, materialCount = 0):
        super().__init__(Mod3Material, materialCount)
        
    def append(self, material):
        if len(material)>=Mod3Material.buffersize:
            raise ValueError("%s is over %d characters and thus incompatible with mod3 format."%(material, Mod3Material.buffersize))
        self.mod3Array.append(Mod3Material({"materialName":material}))
        
    def __getitem__(self,ix):
        return self.mod3Array[ix].materialName
        
    def sceneProperties(self):
        return {"MaterialName%d"%ix:matname.materialName for ix, matname in enumerate(self.mod3Array)}

class Mod3GroupProperty(CS.PyCStruct):
    fields = OrderedDict([
                ("groupID","int"),
                ("CD","int[3]"),
                ("unknf","float[4]")                
                ])

class Mod3GroupProperties(CS.Mod3Container):
    def __init__(self, propertyCount):
        super().__init__(Mod3GroupProperty,propertyCount)
    #requiredProperties = {"groupProperties"}
            
    def construct(self, data):
        data = self.decompose(data)
        #self.count = len(data)
        self.mod3Array = [Mod3GroupProperty() for _ in range(len(data))]
        [x.construct({prop:data[index][prop] for prop in data[index]}) for x,index in zip(self.mod3Array,sorted(data.keys()))]
        return self
    
    def decompose(self,propertyMass):
        indices = {}
        for prop in propertyMass:
            count,propName = prop.split(":")
            count = int(count.replace("GroupProperty",""))
            if count not in indices:
                indices[count]={}
            indices[count][propName] = propertyMass[prop]
        return indices
    
    def sceneProperties(self):
        return {"GroupProperty%d:%s"%(i,field):getattr(data,field)
                for i,data in enumerate(self) for field in Mod3GroupProperty.fields}  
        
#Blind Data Remnants
class GenericRemnants():
    def __init__(self):
        pass
    
    def marshall(self, data):
        byteData = data.read()
        if byteData:
            self.Remnants = struct.unpack('B'*len(byteData),byteData)
        else:
            self.Remnants = []
            
    def construct(self, data):
        self.Remnants = list(data)
        
    def verify(self):
        pass
            
    def serialize(self):
        return b''.join([struct.pack('B', x) for x in self.Remnants])
    def sceneProperties(self):
        return {"TrailingData":self.Remnants}
        
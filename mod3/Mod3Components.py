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
            ("boneMapCount","uint64"),
            ("boneOffset","uint64"),
            ("groupOffset","uint64"),
            ("materialNamesOffset","uint64"),
            ("meshOffset","uint64"),
            ("vertexOffset","uint64"),
            ("facesOffset","uint64"),
            ("unknOffset","uint64"),
            ("unkn1","float[38]"),
            ("unkn2","byte[64]")
            ])
    scenePropertyList = ["vertexIds", "groupCount", "boneMapCount", "materialCount",
                             "unkn1","unkn2"]
    defaultProperties = {"id":0x444F4D,"version":237,"version2":0,"secondBufferSize":0}
    requiredProperties = set(scenePropertyList)
    def sceneProperties(self):
        return {prop:self.__getattribute__(prop)
                for prop in self.scenePropertyList}        
        
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

class Mod3GroupProperties(CS.PyCStruct):
    def __init__(self, propertyCount):
        self.fields = OrderedDict([("groupProperties","int32[%d]"%(propertyCount*8))])
        super().__init__()
    requiredProperties = {"groupProperties"}
    
    def construct(self, groupStuffList):
        self.groupProperties = groupStuffList
        
    def sceneProperties(self):
        return {"GroupProperty%d"%(i):data
                for i,data in enumerate(self.groupProperties)}      
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
        
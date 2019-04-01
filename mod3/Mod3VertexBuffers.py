# -*- coding: utf-8 -*-
"""
Created on Wed Feb  6 23:40:29 2019

@author: AsteriskAmpersand
"""
from collections import OrderedDict
try:
    from ..common import Cstruct as CS
except:
    import sys
    sys.path.insert(0, r'..\common')
    import Cstruct as CS

def dictMerge(d1,d2):
    return OrderedDict(list(d1.items()) + list(d2.items()))
def isIterable(objectInstance):
    try:
        iter(objectInstance)
    except:
        return False
    return True

class Mod3VertexPosition(CS.PyCStruct):
    fields = OrderedDict([
            ("x","float"),
            ("y","float"),
            ("z","float")])
    
    def construct(self, position):
        self.x,self.y,self.z = position
        

class Mod3VertexNormal(CS.PyCStruct):
    fields = OrderedDict([
            ("x","byte"),
            ("y","byte"),
            ("z","byte"),
            ("w","byte")])
    
    def construct(self,normal):
        self.x,self.y,self.z,self.w=normal
    
Mod3VertexTangent = Mod3VertexNormal

class Mod3VertexUV(CS.PyCStruct):
    fields = OrderedDict([
            ("uvX","hfloat"),
            ("uvY","hfloat")])
    
    def construct(self,uv):
        self.uvX,self.uvY = uv

class Mod3VertexColour(CS.PyCStruct):
    fields = OrderedDict([
            ("Red","ubyte"),
            ("Green","ubyte"),
            ("Blue","ubyte"),
            ("Alpha","ubyte"),
            ])
    
    def construct(self, colour):
        self.Red, self.Green, self.Blue, self.Alpha = colour
    
class Mod3VertexJoint(CS.PyCStruct):
    def __init__(self,jointCount):
        self.fields = OrderedDict([
            ("boneIds","ubyte[%d]"%jointCount)
            ])
        super().__init__()

    def construct(self, ids):
        self.boneIds = ids
    
class Mod3VertexWeightBase(CS.PyCStruct):
    WEIGHT_MULTIPLIER = 1023;
    fields = OrderedDict([("tenBitWeight","uint32")])
    
    @staticmethod
    def tenBitWeightSplit(weight):
        weights = []
        for i in range(3):
            weights.append((weight>>(i*10) & 0x3ff))
        return weights
    
    @staticmethod
    def tenBitWeightMerge(weightList):
        return sum([weight<<(10*offset) for offset, weight in enumerate(weightList[:3])])
    
    @staticmethod
    def weightFromBytes(byteWeights):
        return list(map(lambda x: x/Mod3VertexWeightBase.WEIGHT_MULTIPLIER, byteWeights))
    @staticmethod
    def weightToBytes(weights):
        return [round(weight*Mod3VertexWeightBase.WEIGHT_MULTIPLIER) for weight in weights]
    
    def marshall(self, data):
        super().marshall(data)
        self.byteWeights = self.tenBitWeightSplit(self.tenBitWeight)
        self.byteWeights.append(Mod3VertexWeightBase.WEIGHT_MULTIPLIER-sum(self.byteWeights))
        self.weights = Mod3VertexWeightBase.weightFromBytes(self.byteWeights)
        self.bits = self.tenBitWeight>>30 #
        """
        There's only two models that use this 2 bits for anything besides 0s
        E:\MHW\Merged\em\em106\00\mod\em106_00_kazan.mod3
        Zorah Magdaros Map Shell
        E:\MHW\Merged\Assets\evm\evm091\evm091_00\mod\evm091_00.mod3 
        A Xenojiiva model that's not the main xenojiiva model (WHY THE FUCK IS IT IN ASSETS?!)
        """
        
    def construct(self, weightList):
        self.weights = weightList
        self.bits = 0
        
    def serialize(self):
        self.tenBitWeight = Mod3VertexWeightBase.tenBitWeightMerge(Mod3VertexWeightBase.weightToBytes(self.weights))+(self.bits<<30)
        return super().serialize()

class Mod3VertexWeightExtended(CS.PyCStruct):
    WEIGHT_MULTIPLIER = 255;
    fields = OrderedDict([("tenBitWeight","uint32"),
                          ("byteWeights","ubyte[4]")])
    
    
    @staticmethod
    def weightFromBytes(byteWeights):
        return list(map(lambda x: x/Mod3VertexWeightExtended.WEIGHT_MULTIPLIER, byteWeights))
    @staticmethod
    def weightToBytes(weights):
        return [round(weight*Mod3VertexWeightExtended.WEIGHT_MULTIPLIER) for weight in weights]
    
    def marshall(self, data):
        super().marshall(data)
        self.weights = Mod3VertexWeightBase.weightFromBytes(Mod3VertexWeightBase.tenBitWeightSplit(self.tenBitWeight))
        self.weights += Mod3VertexWeightExtended.weightFromBytes(self.byteWeights)
        self.weights.append(1.0-sum(self.byteWeights))
        self.bits = self.tenBitWeight>>30
        
    def construct(self, weightList):
        self.weights = weightList
        self.bits = 0
        
    def serialize(self):
        self.tenBitWeight = Mod3VertexWeightBase.tenBitWeightMerge(Mod3VertexWeightBase.weightToBytes(self.weights[:3]))+(self.bits<<30)
        self.byteWeights = Mod3VertexWeightExtended.weightToBytes(self.weights[3:7])
        return super().serialize()
        

class Mod3Vertex():
    blocklist = {
             0xa756f2f9:{'name':'IANonSkin1UV','uvs':1},
             0xa5104ca0:{'name':'IANonSkin2UV','uvs':2},
             0xc3ac03a1:{'name':'IANonSkin3UVColor','uvs':3,'colour':True},
             0xc9690ab8:{'name':'IANonSkin4UVColor','uvs':4,'colour':True},
             0x818904dc:{'name':'IANonSkin1UVColor','uvs':1,'colour':True},
             0x0f06033f:{'name':'IANonSkin2UVColor','uvs':2,'colour':True},
             0xf637401c:{'name':'IASkin4wt1UV','uvs':1,'weights':4},
             0xf471fe45:{'name':'IASkin4wt2UV','uvs':2,'weights':4},
             0x3c730760:{'name':'IASkin4wt1UVColor','uvs':1,'weights':4,'colour':True},
             0xb2fc0083:{'name':'IASkin4wt2UVColor','uvs':2,'weights':4,'colour':True},
             0x81f58067:{'name':'IASkin8wt1UV','uvs':1,'weights':8},
             0x83b33e3e:{'name':'IASkin8wt2UV','uvs':2,'weights':8},
             0x366995a7:{'name':'IASkin8wt1UVColor','uvs':1,'weights':8,'colour':True},#8 is complement
             0xb8e69244:{'name':'IASkin8wt2UVColor','uvs':2,'weights':8,'colour':True}
             }
    weightScheme = {
            4:Mod3VertexWeightBase,
            8:Mod3VertexWeightExtended        
            }
    
    fields = OrderedDict([
            ("position",Mod3VertexPosition),
            ("normal",Mod3VertexNormal),
            ("tangent",Mod3VertexTangent),
            ("uvs",[Mod3VertexUV]*4),
            #("weights",[Mod3VertexWeightBase, Mod3VertexWeightExtended]),#,
            #("boneIds",[Mod3VertexJoint]*2)
            ])
       
    @staticmethod
    def blockSelect(blockType):
        resulting_field = OrderedDict(list(Mod3Vertex.fields.items()))
        resulting_field['uvs'] = resulting_field['uvs'][:blockType['uvs']]
        if 'weights' in blockType:
            resulting_field['weights'] = Mod3Vertex.weightScheme[blockType['weights']]#REWRITE
            resulting_field['boneIds'] = lambda: Mod3VertexJoint(blockType['weights'])#REWRITE
        if 'colour' in blockType:
            resulting_field['colour'] = Mod3VertexColour
        return resulting_field
    
    def __init__(self, blockType):
        self.blockType = self.blocklist[blockType]
        self.fields = self.blockSelect(self.blockType)
        for attribute in self.fields:
            self.__setattr__(attribute, self.fields[attribute]() if not isIterable(self.fields[attribute]) else [att() for att in self.fields[attribute]])
    
    def marshall(self, data):
        for field in self.fields:
            attribute = self.__getattribute__(field)
            if not isIterable(attribute):
                attribute.marshall(data)
            else:
                [x.marshall(data) for x in attribute]

    def construct(self, data):
        data["weights"],data["boneIds"] = [w for i,w in data["weights"]],[i for i,w in data["weights"]]
        for field in self.fields:
            attribute = self.__getattribute__(field)
            if not isIterable(attribute):
                attribute.construct(data[field])
            else:
                [x.construct(datum) for x,datum in zip(attribute,data[field])]

    def serialize(self):
        result = bytearray()
        for fieldName in self.fields:
            field = self.__getattribute__(fieldName)
            if not isIterable(field):
                result += field.serialize()
            else:
                result += b''.join([entry.serialize() for entry in field])
        return result
            
    def __len__(self):
        return sum((len(self.__getattribute__(field)) if not isIterable(self.__getattribute__(field)) else sum((len(subfield) for subfield in self.__getattribute__(field))) for field in self.fields))
            
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  5 22:29:30 2019

@author: AsteriskAmpersand
"""

from collections import OrderedDict
try:
    from ..common import Cstruct as CS
    from ..mod3.Matrices import Matrix
except:
    import sys
    sys.path.insert(0, r'..\common')
    sys.path.insert(0, r'..\mod3')
    import Cstruct as CS
    from Matrices import Matrix    

class Mod3Bone(CS.PyCStruct):
    fields = OrderedDict([
            ("boneFunction","short"),
            ("parentId","ubyte"),
            ("child","ubyte"),
            ("unkn2","float"),
            ("length","float"),
            ("x","float"),
            ("y","float"),
            ("z","float")  
            ])
    requiredPropeties = {f for f in fields}
    
    def __init__(self, data = None, **kwargs):
        super().__init__(data, **kwargs)
        self.IK = False
        
    def suspectIK(self):
        return self.length==0#self.parentId != 255 and 
    
    def markIK(self):
        self.IK=True
        
    def unmarkIK(self):
        self.IK=False
        
    def fakeCoreProperties(self, parent, LMat, AMat):
        vec = self.positionVector()
        res = (self.positionVector() + AMat*vec).matrix[0]#(1/(self.unkn2 if self.unkn2 else 1)*
        return {"parentId":self.parentId,
                "x":res[0],
                "y":res[1],
                "z":res[2]}
        
    def positionVector(self):
        mat = Matrix((4,1))
        mat.matrix = [[self.x,self.y,self.z,1.0]]
        return mat
        
    def coreProperties(self):
        return {"parentId":self.parentId,
                "x":self.x,
                "y":self.y,
                "z":self.z}
        
    def customProperties(self):
        return {"boneFunction":self.boneFunction,
                "child":self.child,
                "unkn2":self.unkn2,
                }
        
    
class Mod3Skeleton(CS.Mod3Container):
    def __init__(self, boneCount = 0):
        super().__init__(Mod3Bone, boneCount)
        
class Mod3Matrices(CS.Mod3Container):
    def __init__(self, boneCount = 0):
        super().__init__(lambda: Matrix([4,4]), boneCount)
           

class Mod3MatrixBundle():
    def __init__(self, boneCount = 0):
        self.LMatrices = Mod3Matrices(boneCount)
        self.AMatrices = Mod3Matrices(boneCount)
        
    def append(self, lmatrix, amatrix):
        self.LMatrices.append(lmatrix)
        self.AMatrices.append(amatrix)
        
    def marshall(self, data):
        self.LMatrices.marshall(data)
        self.AMatrices.marshall(data)
        
    def construct(self, lmatrices, amatrices):
        self.LMatrices.construct(lmatrices)
        self.AMatrices.construct(amatrices)
        
    def verify(self):
        self.LMatrices.verify()
        self.AMatrices.verify()
        
    def serialize(self):
        return self.LMatrices.serialize() + self.AMatrices.serialize()
    
    def __getitem__(self, ix):
        return (self.LMatrices[ix], self.AMatrices[ix])
    
    def __iter__(self):
        return zip(self.LMatrices, self.AMatrices).__iter__()
    
    def __len__(self):
        return len(self.LMatrices)+len(self.AMatrices)
    
    def pop(self, ix):
        self.LMatrices.pop(ix)
        self.AMatrices.pop(ix)
        
class StateError(Exception):
    pass

class Mod3SkelletalStructure():   
    def __init__(self, boneCount):
        self.Skeleton = Mod3Skeleton(boneCount)
        self.Matrices = Mod3MatrixBundle(boneCount)
        self.BoneMap = Mod3BoneMap(boneCount)
        
    def marshall(self, data):
        self.Skeleton.marshall(data)
        self.Matrices.marshall(data)
        self.BoneMap.marshall(data)
        
    def construct(self, skeleton, lmatrices, amatrices):
        self.Skeleton.construct(skeleton) 
        self.Matrices.construct(lmatrices, amatrices)
        self.foldSkeletonToMap()
    
    def serialize(self):
        return self.Skeleton.serialize()+self.Matrices.serialize()+self.BoneMap.serialize()
    
    def verify(self):
        self.Skeleton.verify()
        self.Matrices.verify()
        self.BoneMap.verify()
    
    def identifyIK(self):
        for ix, bone in enumerate(self.Skeleton):
            if bone.suspectIK():#Aberrant relationship (chained 0s)
                bone.markIK()         
    
    def unfoldMapToSkeleton(self):
        families = self.BoneMap.unfold()
        for bone, function in families:
            self.Skeleton[bone].boneFunction = function
            
    def foldSkeletonToMap(self):
        self.BoneMap.fold(self.Skeleton)       
        
    def traditionalSkeletonStructure(self):
        self.identifyIK()

        return [{**b.coreProperties(),#b.fakeCoreProperties((self.Skeleton[b.parentId] if b.parentId!=255 else None),l,a),#
                 #AMat[p_x] = LMat[p_x].inverted() * AMat[p_x-1] where p_x is a chain of bones and p_x-1 is p_x parent
                **{"LMatCol%d"%ix:col for ix,col in enumerate(l.columnRepresentation())},
                #**{"AMatCol%d"%ix:col for ix,col in enumerate(a.columnRepresentation())},
                "CustomProperties":{**b.customProperties()}
                }for b,(l,a) in zip(self.Skeleton, self.Matrices)]    
                
    def Count(self):
        return self.Skeleton.Count()
        
    def __len__(self):
        return len(self.Skeleton)+len(self.Matrices)+len(self.BoneMap)


class Mod3BoneMap(CS.PyCStruct):
    boneRemapCount = 512
    def __init__(self,boneCount):
        self.boneRemapCount = Mod3BoneMap.boneRemapCount*(boneCount!=0)
        self.fields = OrderedDict([('boneRemap','ubyte[%d]'%self.boneRemapCount)])
        super().__init__()
    
    def unfold(self):#Bone map to dictionary of bones with their "animation position"
        boneProperties = {}
        for entryNum, mapping in enumerate(self.boneRemapCount):
            if mapping not in boneProperties:
                boneProperties[mapping]=entryNum
            else:
                raise ValueError("Bone %d has multiple functions assigned by the BoneMap."%mapping)
            
    def fold(self, skeleton):#skeleton with custom property to bonemap)
        self.boneRemap = [255]*self.boneRemapCount
        for bIndex, bone in enumerate(skeleton):
            if not bone.boneFunction == 512:
                self.boneRemap[bone.boneFunction] = bIndex
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 13:18:43 2019

@author: AsteriskAmpersand
"""
try:
    from ..mod3 import Mod3Components as Mod3C
    from ..mod3 import Mod3Mesh as Mod3M
    from ..mod3 import Mod3Skeleton as Mod3S
    from ..mod3.Mod3VertexBuffers import Mod3Vertex
except:
    import sys
    sys.path.insert(0, r'..\mod3')
    import Mod3Components as Mod3C
    import Mod3Mesh as Mod3M
    import Mod3Skeleton as Mod3S
    from Mod3VertexBuffers import Mod3Vertex    

class Mod3():    
    def __init__(self):
        self.Header = Mod3C.MOD3Header
        self.Skeleton = Mod3S.Mod3SkelletalStructure
        self.GroupProperties = Mod3C.Mod3GroupProperties#Can be completely nulled out for no risk
        self.Materials = Mod3C.Mod3Materials
        self.MeshParts = Mod3M.Mod3MeshCollection
        self.Trailing = Mod3C.GenericRemnants
        
    def marshall(self, data):
        self.Header = self.Header()
        self.Header.marshall(data)
        data.seek(self.Header.boneOffset)
        self.Skeleton = self.Skeleton(self.Header.boneCount)
        self.Skeleton.marshall(data)
        data.seek(self.Header.groupOffset)
        self.GroupProperties = self.GroupProperties(self.Header.groupCount)
        self.GroupProperties.marshall(data)
        data.seek(self.Header.materialNamesOffset)
        self.Materials = self.Materials(self.Header.materialCount)
        self.Materials.marshall(data)
        data.seek(self.Header.meshOffset)
        self.MeshParts = self.MeshParts(self.Header.meshCount, self.Header.vertexOffset, self.Header.facesOffset)
        self.MeshParts.marshall(data)
        data.seek(self.Header.trailOffset)
        self.Trailing = self.Trailing()
        self.Trailing.marshall(data)

    def construct(self, fileHeader, materials, groupStuff, skeleton, lmatrices, amatrices, meshparts, trailingData):
        self.Header = self.Header()
        self.Header.construct(fileHeader)
        self.Skeleton = self.Skeleton(len(skeleton))
        self.Skeleton.construct(skeleton,lmatrices,amatrices)
        self.GroupProperties = self.GroupProperties(self.Header.groupCount)
        self.GroupProperties.construct(groupStuff)
        self.Materials = self.Materials(len(materials))
        self.Materials.construct(materials)
        self.MeshParts = self.MeshParts(len(meshparts))
        self.MeshParts.construct(meshparts)
        self.Trailing = self.Trailing()
        self.Trailing.construct(trailingData)
        self.calculateCountsOffsets()
        self.MeshParts.realignFaces()
        self.verify()
        
    def verify(self):
        self.Header.verify()
        self.Skeleton.verify()
        self.GroupProperties.verify()
        self.Materials.verify()
        self.MeshParts.verify()
        self.Trailing.verify()

    @staticmethod
    def pad(current,finalposition):
        return b''.join([b'\x00']*(finalposition-current))
           
    def calculateCountsOffsets(self):
        #TODO - Sanity Checks
        vCount, fCount, vBufferLen = self.MeshParts.updateCountsOffsets()
    
        #Header
        #("boneCount","short"),
        self.Header.boneCount = self.Skeleton.Count()
        #("meshCount","short"),
        self.Header.meshCount = self.MeshParts.Count()
        #("materialCount","short"),
        self.Header.materialCount = self.Materials.Count()
        #("vertexCount","long"),
        self.Header.vertexCount = vCount
        #("faceCount","long"),
        self.Header.faceCount = fCount*3
        #("vertexIds","long"),#notModifiedEver
        #("vertexBufferSize","long"),#length of vertices section
        self.Header.vertexBufferSize = vBufferLen
        #("secondBufferSize","long"),#unused
        #("groupCount","uint64"),#unchanged
        self.Header.boneCount = self.Skeleton.Count()
        
        currentOffset = len(self.Header)
        #("boneOffset","uint64"),
        self.Header.boneOffset = self.align(currentOffset) if self.Header.boneCount else 0
        #("groupOffset","uint64"),
        currentOffset = self.Header.groupOffset = self.align(currentOffset+len(self.Skeleton))
        #("materialNamesOffset","uint64"),
        currentOffset = self.Header.materialNamesOffset = self.align(currentOffset+len(self.GroupProperties))
        #("meshOffset","uint64"),
        self.Header.meshOffset = self.align(currentOffset + len(self.Materials))
        #("vertexOffset","uint64"),
        self.Header.vertexOffset = self.Header.meshOffset + self.MeshParts.getVertexOffset()
        #("facesOffset","uint64"),
        self.Header.facesOffset = self.Header.meshOffset + self.MeshParts.getFacesOffset()
        #("unknOffset","uint64"),
        self.Header.trailOffset = self.align(self.Header.meshOffset + self.MeshParts.getBlockOffset(),4)
          
    @staticmethod
    def align(offset, grid = 16):
        return offset+(grid - offset%grid if offset%grid else 0)
    
    def serialize(self):
        serialization = b''
        serialization+=self.Header.serialize()
        serialization+=self.pad(len(serialization),self.Header.boneOffset)
        serialization+=self.Skeleton.serialize()
        serialization+=self.pad(len(serialization),self.Header.groupOffset)
        serialization+=self.GroupProperties.serialize()
        serialization+=self.pad(len(serialization),self.Header.materialNamesOffset)
        serialization+=self.Materials.serialize()
        serialization+=self.pad(len(serialization),self.Header.meshOffset)
        serialization+=self.MeshParts.serialize()
        serialization+=self.pad(len(serialization),self.Header.trailOffset)
        serialization+=self.Trailing.serialize()
        return serialization
    
    def boundingBoxes(self):
        return self.MeshParts.boundingBoxes()
    
    def sceneProperties(self):
        sceneProp = self.Header.sceneProperties()
        sceneProp.update(self.Materials.sceneProperties())
        sceneProp.update(self.GroupProperties.sceneProperties())
        sceneProp.update(self.Trailing.sceneProperties())
        #TODO - Separate properties per sections leave only Header, Materials and Trailing
        return sceneProp
    
    def prepareArmature(self):
        return self.Skeleton.traditionalSkeletonStructure()  

    def meshProperties(self):
        return self.MeshParts.sceneProperties()
    
    def prepareMeshparts(self, weightSplit):
        meshes = []
        for traditionalMesh in self.MeshParts.traditionalMeshStructure(weightSplit):
            traditionalMesh["properties"]["material"] = self.Materials[traditionalMesh["properties"]["materialIdx"]]
            traditionalMesh["properties"].pop("materialIdx")
            traditionalMesh["properties"]["blockLabel"] = Mod3Vertex.blocklist[traditionalMesh["properties"]["blocktype"]]["name"]
            traditionalMesh["properties"].pop("blocktype")
            meshes.append(traditionalMesh)
        return meshes
    
    def filterLOD(self):
        self.MeshParts.filterLOD()

def doublesidedEval(v1, v2):
    if v1 != v2:
        print(v1)
        print(v2)
        raise ValueError()        

if __name__ in "__main__":
    import FileLike as FL
    from pathlib import Path
    modelf = Path(r'C:\Users\Asterisk\Downloads\f_leg040_0010.mod3')
    modelfile = FL.FileLike(modelf.open("rb").read())
    model = Mod3()
    model.marshall(modelfile)
    model.MeshParts.traditionalMeshStructure()
    raise
    from mathutils import Matrix
    def worldMatrix(bone,lmat,lmats,skeleton):
        if bone.parentId == 255:
            bone.world = Matrix(lmat.matrix).transposed()
            return bone.world
        if not hasattr(skeleton[bone.parentId],"world"):
            worldMatrix(skeleton[bone.parentId],lmats[bone.parentId],lmats,skeleton)
        bone.world =  skeleton[bone.parentId].world @ Matrix(lmat.matrix).transposed()
        return bone.world
        
    sys.path.insert(0, r'..\common')
    
    chunkpath = Path(r"D:\Games SSD\MHW\chunk\em")
    values = set()
    #with open(r"G:\Wisdom\modelData.txt","w") as outf:
    #    def print(*args):
    #        x: outf.write(''.join(map(str,args))+'\n')
    unkn1 = [set() for i in range(64)]
    unkn3 = {}
    intUnkn = {}
    
    for modelf in chunkpath.rglob("*.mod3"):
        if "tail" in str(modelf) or "horn" in str(modelf):
            continue
        printf = False
        try:
            #modelf = Path(r"E:\MHW\chunkG0\accessory\askill\askill001\mod\common\askill_mantle001.mod3")
            modelfile = FL.FileLike(modelf.open("rb").read())
            model = Mod3()
            model.marshall(modelfile)
            deepest = -1
            depth = 0
            mat = None
            for bone, lmat in zip(model.Skeleton.Skeleton, model.Skeleton.Matrices.LMatrices):
                wmat = worldMatrix(bone,lmat,model.Skeleton.Matrices.LMatrices,model.Skeleton.Skeleton)
                if wmat[2][3] < depth:
                    deepest = bone
                    depth = wmat[2][3]
                    mat = wmat
                    #print(wmat)
                    #print(bone.boneFunction)
            parent = deepest.parentId
            chain = [deepest]
            while parent != 255:
                bone = model.Skeleton.Skeleton[parent]
                chain.append(bone)
                parent = bone.parentId
            print(modelf)
            print('->'.join(reversed(list((str(b.boneFunction) for b in chain)))))
            print("Probable Spine",chain[max(min(len(chain)-1,round(len(chain)*2/3)),0)].boneFunction)
            print("Probable Tail Center",chain[max(min(len(chain)-1,round(len(chain)*1/3)),0)].boneFunction)
            #raise
        except:
            pass
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  5 22:36:21 2019

@author: AsteriskAmpersand
"""

from collections import OrderedDict, Counter
from mathutils import Vector, Matrix
try:
    from ..common import Cstruct as CS
    from ..mod3.Mod3VertexBuffers import Mod3Vertex
except:
    import sys
    sys.path.insert(0, r'..\common')
    sys.path.insert(0, r'..\mod3')
    import Cstruct as CS
    from Mod3VertexBuffers import Mod3Vertex    
    
class Mod3MeshPartHeader(CS.PyCStruct):
    fields = OrderedDict([
            ("unkn","short"),
            ("vertexCount","ushort"),
            ("visibleCondition","ushort"),
            ("materialIdx","ushort"),
            ("lod","long"),
            ("unkn2","short"),
            ("blockSize","ubyte"),
            ("unkn3","byte"),
            ("vertexSub","ulong"),
            ("vertexOffset","ulong"),
            ("blocktype","ulong"),
            ("faceOffset","ulong"),
            ("faceCount","ulong"),
            ("vertexBase","ulong"),
            ("boneremapid","ubyte"),
            ("unkn9","ubyte[39]")
            ])
        
    requiredProperties = ["unkn","visibleCondition","lod","unkn2","unkn3","blocktype",
                    "boneremapid","unkn9", "materialIdx"]  
    #"materialIdx"      
    def externalProperties(self):
        return {prop:self.__getattribute__(prop)
                for prop in self.requiredProperties}
    
class Mod3Mesh():
#Header+Vertex+Faces
    def __init__(self, vertexOffset, faceOffset):
        self.Header = Mod3MeshPartHeader()
        self.Vertices = []
        self.Faces = []
        self.vertexOffset = vertexOffset
        self.faceOffset = faceOffset
        
    def marshall(self, data):
        self.Header.marshall(data)
        position = data.tell()
        data.seek((self.vertexOffset+self.Header.vertexOffset)+(self.Header.blockSize*(self.Header.vertexSub+self.Header.vertexBase)))
        self.Vertices = [Mod3Vertex(self.Header.blocktype) for _ in range(self.Header.vertexCount)]
        for vert in self.Vertices:
            vert.marshall(data)
        self.Faces = [Mod3Face() for _ in range(self.Header.faceCount//3)]
        data.seek(self.faceOffset+self.Header.faceOffset*2)
        for face in self.Faces:
            face.marshall(data)
        data.seek(position)
        
    #{"mesh":pymesh, "faces":faces, "properties":meshProp, "meshname":mesh.name}
    def construct(self, mesh):
        header = mesh["properties"]
        faces = mesh["faces"]
        vertices = mesh["mesh"]
        self.Header.construct(header)
        self.Header.blockSize = len(Mod3Vertex(self.Header.blocktype))
        self.Faces = [Mod3Face() for _ in faces]
        for modface, blenface in zip(self.Faces, faces):
            modface.construct(blenface)
        self.Vertices = [Mod3Vertex(self.Header.blocktype) for _ in vertices]
        for modvert, blenvert in zip(self.Vertices,vertices):
            modvert.construct(blenvert)
            
    def verify(self):
        self.Header.verify()
        [(v.verify(),f.verify()) for v,f in zip(self.Vertices,self.Faces)]
        
        
    def serialize(self):
        return self.Header.serialize(), \
                b''.join([vertex.serialize() for vertex in self.Vertices]), \
                b''.join([face.serialize() for face in self.Faces])

    def updateCounts(self):
        self.Header.vertexCount = self.vertexCount()
        self.Header.faceCount = self.faceCount()*3

    def updateVertexOffsets(self, prevSub, prevBase, prevVertCount, prevOffset, prevBlockSize):
            #When blocksizes are equal Sub increases
            #when different the sub becomes an offset and resets
            #when Sub would exceed WITH CURRENT COUNT it instead goes to Base
            blockSize = self.Header.blockSize
            if self.Header.blockSize != prevBlockSize:
                self.Header.vertexOffset = prevSub + prevBase + prevVertCount + prevOffset
                self.Header.vertexSub = 0
                self.Header.vertexBase = 0
            else:
                prevSub, prevBase, prevVertCount= prevSub//blockSize,prevBase//blockSize,prevVertCount//blockSize
                if self.Header.vertexCount + prevSub + prevVertCount > 0xFFFF:
                    self.Header.vertexSub = 0
                    self.Header.vertexBase = prevSub + prevBase + prevVertCount
                else:
                    self.Header.vertexSub =  prevSub + prevVertCount
                    self.Header.vertexBase = prevBase
                self.Header.vertexOffset = prevOffset
            return self.Header.vertexSub*blockSize, self.Header.vertexBase*blockSize, self.Header.vertexCount*blockSize, self.Header.vertexOffset, self.Header.blockSize
               
    def updateFaceOffsets(self, baseOffset, currentOffset):
        self.faceOffset = baseOffset
        if currentOffset % 2:
            raise ValueError("Uneven face offset")
        self.Header.faceOffset = currentOffset//2
        return self.faceCount()*len(Mod3Face())+currentOffset    
    
    @staticmethod
    def splitWeightFunction(zippedWeightBones, slash = False):
        #Might Require Remembering Negative Weight Bones
        extension = (lambda x: "/%d"%x) if slash else (lambda x: "")
        currentBones = Counter()
        result = {}
        for ix, (bone, weight) in enumerate(zippedWeightBones[:-1]):
            if bone in currentBones:
                boneName,_ = (bone,"%d%s"%(currentBones[bone],extension(ix))), currentBones.update([bone])
            else:
                currentBones[bone]=1
                boneName = (bone,"%d%s"%(0,extension(ix)))
            result[boneName]=max(weight,0.0)
        bone, weight = zippedWeightBones[-1]
        boneName = (bone,"%d%s"%(-1, extension(ix+1)))
        result[boneName]=max(weight,0.0)
        return result
    
    @staticmethod
    def slashWeightFunction(zippedWeightBones):
        return Mod3Mesh.splitWeightFunction(zippedWeightBones, slash = True)
    
    @staticmethod
    def unifiedWeightFunction(zippedWeightBones):
        keys = set([bone for bone, weight in zippedWeightBones])# if bone!=0])
        return {key:max(min(sum([weight for bone, weight in zippedWeightBones if bone == key]),1.0),0.0) for key in keys}         
    
    @staticmethod
    def dictWeightAddition(baseDictionary, dictionary, ix):
        for key in dictionary:
            if key not in baseDictionary:
                baseDictionary[key] = [(ix, dictionary[key])]
            else:
                baseDictionary[key] += [(ix, dictionary[key])]

    @staticmethod
    def weightFunctionSelector(x): return {0:Mod3Mesh.unifiedWeightFunction, 
                                            1:Mod3Mesh.splitWeightFunction,
                                            2:Mod3Mesh.slashWeightFunction
                                            }[x]
    def decomposeVertices(self, vertices, splitWeights):
        additionalFields = Mod3Vertex.blocklist[self.Header.blocktype]
        weightGroups = {}
        colour = []        
        if "weights" in additionalFields:
            weightFunction = self.weightFunctionSelector(splitWeights)
            for ix, vertex in enumerate(vertices):
                self.dictWeightAddition(weightGroups, weightFunction(list(zip(vertex.boneIds.boneIds,vertex.weights.weights))),ix)
        if "colour" in additionalFields:
            colour = [vertex.colour for vertex in vertices]
        flat_vertices = [(vertex.position.x, vertex.position.y, vertex.position.z) for vertex in vertices]
        normals = [(vertex.normal.x, vertex.normal.y, vertex.normal.z) for vertex in vertices]
        tangents = [(vertex.tangent.x, vertex.tangent.y, vertex.tangent.z, vertex.tangent.w) for vertex in vertices]
        uvs = list(map(list, list(zip(*[[(uv.uvX, 1-uv.uvY) for uv in vertex.uvs] for vertex in vertices]))))
        return flat_vertices, weightGroups, normals, tangents, uvs, colour
    
    def traditionalMeshStructure(self, splitWeights):
        properties = self.Header.externalProperties()
        faces = [[face.v1, face.v2, face.v3] for face in self.Faces]
        vertices, weightGroups, normals, tangents, uvs, colour = self.decomposeVertices(self.Vertices, splitWeights)
        return {"vertices":vertices, "properties":properties, "faces":faces, 
                "weightGroups":weightGroups, "normals":normals, "tangents":tangents, 
                "uvs":uvs, "colour":colour}
        
    def faceCount(self):
        return len(self.Faces)
    
    def vertexCount(self):
        return len(self.Vertices)
    
    def vertexBuffer(self):
        return self.Header.blockSize*self.vertexCount()
    
    def faceBuffer(self):
        return sum([len(face) for face in self.Faces])
    
    def edgeCount(self):
        return len(set(sum(map(lambda x: x.edges(), self.Faces),[])))
    
    #Len

class Mod3MeshCollection():
    def __init__(self, meshCount=0, vertexOffset=None, faceOffset=None):
        self.Meshes = [Mod3Mesh(vertexOffset, faceOffset) for _ in range(meshCount)]
        self.MeshProperties = Mod3MeshProperties()
        self.vertexOffset = vertexOffset
        self.faceOffset = faceOffset
        
    def marshall(self, data):
        for mesh in self.Meshes:
            pos = data.tell()
            try:
                mesh.marshall(data)
            except:
                data.seek(pos+len(Mod3MeshPartHeader()))
        self.MeshProperties.marshall(data)
        
    def serialize(self):
        meshes, vertices, faces = [],[],[]
        for mesh in self.Meshes:
            m,v,f = mesh.serialize()
            meshes.append(m)
            vertices.append(v)
            faces.append(f)
        return b''.join(meshes)+self.MeshProperties.serialize()+b''.join(vertices)+b''.join(faces)
    
    def construct(self, meshparts, meshData):
        for blenMesh,modMesh in zip(meshparts, self.Meshes):
            modMesh.construct(blenMesh)
        #self.Meshes.sort(key = lambda x: x.Header.blockSize)
        self.MeshProperties.construct(meshData)
        
    def verify(self):
        [m.verify for m in self.Meshes]
        self.MeshProperties.verify()
    
    def Count(self):
        return len(self.Meshes)
    
    #def __len__(self):
    #    return sum([len(mesh) for mesh in self.Meshes]) + len(self.MeshProperties)
    
    def realignFaces(self):
        #TODO: for each meshpart add vertexsub to each face
        for mesh in self.Meshes:
            for face in mesh.Faces:
                face.adjust(mesh.Header.vertexSub)
    
    def updateCountsOffsets(self):
        #Meshparts
        #("vertexSub","ulong"),
        #("vertexOffset","ulong"),
        #("faceOffset","ulong"),
        #("vertexBase","ulong"),
        vCount = 0
        fCount = 0
        vBufferLen = 0
        
        prevSub = 0
        prevBase = 0
        prevVertCount = 0
        prevBlockSize = 0
        prevOffset = 0
        for mesh in self.Meshes:
            mesh.updateCounts()
            prevSub, prevBase, prevVertCount, prevOffset, prevBlockSize = mesh.updateVertexOffsets(prevSub, prevBase, prevVertCount, prevOffset, prevBlockSize)
            vCount+=mesh.vertexCount()
            fCount+=mesh.faceCount()
            vBufferLen+=mesh.vertexBuffer()
        self.vertexOffset = len(Mod3Mesh(0,0).Header)*len(self.Meshes) + len(self.MeshProperties)
        self.faceOffset = self.vertexOffset + vBufferLen
        currentFaceOffset = 0
        for mesh in self.Meshes:
            currentFaceOffset=mesh.updateFaceOffsets(self.faceOffset, currentFaceOffset)
        return vCount, fCount, vBufferLen
    
    def getVertexOffset(self):
        return self.vertexOffset
    
    def getFacesOffset(self):
        return self.faceOffset
    
    def getBlockOffset(self):
        return self.faceOffset + sum([mesh.faceBuffer() for mesh in self.Meshes])
    
    def getEdgeCount(self):
        return sum(map(lambda x: x.edgeCount(), self.Meshes))
    
    def sceneProperties(self):
        return self.MeshProperties.sceneProperties()
    
    def boundingBoxes(self):
        return self.MeshProperties.boundingBoxes()
    
    def __getitem__(self, ix):
        return self.Meshes[ix]
    
    def __iter__(self):
        return self.Meshes.__iter__()
    
    def traditionalMeshStructure(self, splitWeights=False):
        tMeshCollection = []
        for mesh in self.Meshes: 
            tMesh = mesh.traditionalMeshStructure(splitWeights)
            tMesh['faces'] = [list(map(lambda x: x-mesh.Header.vertexSub, faceindices)) for faceindices in tMesh['faces']]
            tMeshCollection.append(tMesh)
        return tMeshCollection
    
    def filterLOD(self):
        self.Meshes = [ mesh for mesh in self.Meshes if mesh.Header.lod == 1 or mesh.Header.lod==0xFFFF ]
    
class Mod3Face(CS.PyCStruct):
    fields = OrderedDict([
            ("v1","ushort"),
            ("v2","ushort"),
            ("v3","ushort"),
            ])
    requiredProperties = {f for f in fields}
    def edges(self):
        return [tuple(sorted([self.v1,self.v2])),
                tuple(sorted([self.v2,self.v3])),
                tuple(sorted([self.v3,self.v1]))]

    def adjust(self,adjustment):
        for field in self.fields:
            self.__setattr__(field, self.__getattribute__(field)+adjustment)
        
class BoundingBox():
    def __init__(self,mod3bb):
        self._center = Vector(mod3bb.center)
        self._dimensions = Vector((Vector(mod3bb.boxMax)-Vector(mod3bb.boxMin))[:3])
        mat = mod3bb.matrix
        #rows = [[mat[i+4*e] for e in range(4)] for i in range(4)]
        rows = [[mat[4*i+e] for e in range(4)] for i in range(4)]
        self._matrix = Matrix(rows)
        self._vector = Vector(mod3bb.vector)[:3]
        self._boneIndex = mod3bb.boneIndex
        self._metadata = {field:getattr(mod3bb,field) for field in Mod3MeshProperty.fields}
    def center(self):
        return self._center
    def scale(self):
        return self._dimensions
    def metadata(self):
        return self._metadata
    def matrix(self):
        return self._matrix
    def vector(self):
        return self._vector
    def bone(self):
        return self._boneIndex
    

class Mod3MeshProperty(CS.PyCStruct):
    fields = OrderedDict([
            ("boneIndex","int"),
            ("spacer","int[3]"),
            ("center","float[3]"),
            ("radius","float"),
            ("boxMin","float[4]"),
            ("boxMax","float[4]"),
            ("matrix","float[16]"),
            ("vector","float[4]"),
            ])
    requiredProperties = { f for f in fields }
    def sceneProperties(self):
        return {field:getattr(self,field) for field in self.fields}
    def boundingBox(self):
        return BoundingBox(self)

class Mod3MeshProperties(CS.PyCStruct):
    fields = OrderedDict([("count","uint")])
    
    def marshall(self, data):
        super().marshall(data)
        self.properties = [Mod3MeshProperty() for _ in range(self.count)]
        [x.marshall(data) for x in  self.properties]
        
    def construct(self, data):
        data = self.decompose(data)
        self.count = len(data)
        self.properties = [Mod3MeshProperty() for _ in range(self.count)]
        [x.construct({prop:data[index][prop] for prop in data[index]}) for x,index in zip(self.properties,sorted(data.keys()))]
        return self
    
    def decompose(self,propertyMass):
        indices = {}
        for prop in propertyMass:
            count,propName = prop.split(":")
            count = int(count.replace("MeshProperty",""))
            if count not in indices:
                indices[count]={}
            indices[count][propName] = propertyMass[prop]
        return indices
    
    def serialize(self):
        return super().serialize() + b''.join([prop.serialize() for prop in self.properties])
    
    def __len__(self):
        return super().__len__() + sum([len(prop) for prop in self.properties])
    
    def sceneProperties(self):
        properties = {"MeshProperty%d:%s"%(ix,prop):val for ix, propertyFamily in enumerate(self.properties) for prop,val in propertyFamily.sceneProperties().items()}
        properties["MeshPropertyCount"]=self.count
        return properties
    
    def boundingBoxes(self):
        return [prop.boundingBox() for prop in self.properties]
    
    def verify(self):
        if self.count == None:
            raise AssertionError("Attribute %s is not initialized."%"count")
        super().verify()

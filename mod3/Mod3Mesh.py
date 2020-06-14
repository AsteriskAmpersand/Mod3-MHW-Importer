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
            ("shadowCast","short"),
              #19: Normal Shadows
            ("vertexCount","ushort"),#Count of vertices
            ("visibleCondition","ushort"),
            ("materialIdx","ushort"),
            ("lod","long"),
            ("weightDynamics","short"),
               #01:        1 - No bone weights
               #03:       11 - No bone weights
               #05:      101 - No bone weights
               #07:      111 - No bone weights
               #09:     1001 - One bone movement
               #11:     1011 - One bone movement
               #13:     1101 - One bone movement, but more than one weight per mesh
               #15:     1111 - One bone movement
               #17:    10001
               #25:    11001 - Multibone Movement
               #33:   100001 - Multibone Movement
               #41:   101001
               #49:   110001
               #57:   111001
               #65:  1000001 - 8wt Multibone Movement (8wt required)
               #129:10000001 - 8wt Multibone Movement (8wt required)
            ("blockSize","ubyte"),
            ("unkn3","byte"),
            ("vertexSub","ulong"),#Running subtotal of vertices of the same kind before spill (0xFFFF) before current
            ("vertexOffset","ulong"),#Offset to start of current kind vertex block within vertex array
            ("blocktype","ulong"),
            ("faceOffset","ulong"),#Offset to start of faces within face array
            ("faceCount","ulong"),#Count of faces
            ("vertexBase","ulong"),#Running subtotal of spilled vertices of the same kind 
            ("NULL_0","ubyte"),#0
            ("boundingBoxCount","ubyte"),
            ("unknownIndex","ushort"),
            ("vertexSubMirror","ushort"),#Copy of Vertex Sub
            ("vertexIndexSub","ushort"),#Current last vertex index on the subtotal (Subtotal + Count - 1) after current
            ("mapData","short[2]"),#Not FF on maps
            ("NULL_1","int"),
            ("intUnknown","int"),
            ("vertexSubTotal","ulong"),#Vertex running subtotal cumulative
            ("NULL_2","int[4]")
            ])
    defaultProperties = {"NULL_0":0,"NULL_1":0,"NULL_2":[0]*4,"boundingBoxCount":None}
    requiredProperties = ["shadowCast","visibleCondition","lod",
                          "weightDynamics","unkn3","blocktype","mapData",
                          "unknownIndex", "intUnknown", "materialIdx"]  
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
        self.BoundingBoxes = []
        
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
        boxes = mesh["boundingBoxes"]
        self.Header.construct(header)
        self.Header.blockSize = len(Mod3Vertex(self.Header.blocktype))
        self.Header.boundingBoxCount = len(boxes)
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

    def updateVertexOffsets(self,
                            vCount, 
                            vBufferLen,
                            prevBase,
                            prevVertexSub,
                            prevBlockSize):
            #When blocksizes are equal Sub increases
            #when different the sub becomes an offset and resets
            #when Sub would exceed WITH CURRENT COUNT it instead goes to Base
            #print(("%07d | "*5)%(vCount,vBufferLen,prevBase,prevVertexSub,prevBlockSize))
            h = self.Header
            
            if h.blockSize != prevBlockSize:
                h.vertexOffset = vBufferLen
                h.vertexSub = 0
                h.vertexBase = 0            
            else:
                if h.vertexCount + prevVertexSub > 0xFFFF:
                    h.vertexSub = 0
                    h.vertexBase = prevBase + prevVertexSub
                else:
                    h.vertexSub =  prevVertexSub
                    h.vertexBase = prevBase
                h.vertexOffset = vBufferLen-(h.vertexBase+h.vertexSub)*h.blockSize
            h.vertexSubMirror = h.vertexSub
            h.vertexSubTotal =  vCount
            h.vertexIndexSub = h.vertexSub + h.vertexCount -1
            return (vCount+h.vertexCount, 
                    vBufferLen+h.vertexCount*h.blockSize,
                    h.vertexBase,
                    h.vertexSub + h.vertexCount,
                    h.blockSize)
            #prevSub, prevBase, prevVertSub, prevVertTotal, prevOffset, prevBlockSize
        
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
                "uvs":uvs, "colour":colour, "boundingBoxes":self.BoundingBoxes}
        
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
        self.BoundingBoxes = Mod3BoundingBoxes()
        self.vertexOffset = vertexOffset
        self.faceOffset = faceOffset
        
    def marshall(self, data):
        for mesh in self.Meshes:
            pos = data.tell()
            try:
                mesh.marshall(data)
            except:
                data.seek(pos+len(Mod3MeshPartHeader()))
        self.BoundingBoxes.marshall(data)
        BoundingBoxes = iter(self.BoundingBoxes)
        for mesh in self.Meshes:            
            for _ in range(mesh.Header.boundingBoxCount):
                mesh.BoundingBoxes.append(next(BoundingBoxes))
        
    def serialize(self):
        meshes, vertices, faces = [],[],[]
        for mesh in self.Meshes:
            m,v,f = mesh.serialize()
            meshes.append(m)
            vertices.append(v)
            faces.append(f)
        return b''.join(meshes)+self.BoundingBoxes.serialize()+b''.join(vertices)+b''.join(faces)
    
    def construct(self, meshparts):
        for blenMesh,modMesh in zip(meshparts, self.Meshes):
            modMesh.construct(blenMesh)
            
        #self.Meshes.sort(key = lambda x: x.Header.blockSize)
        self.BoundingBoxes.construct(sum(map(lambda x:x["boundingBoxes"],meshparts),[]))
        
    def verify(self):
        [m.verify for m in self.Meshes]
        self.BoundingBoxes.verify()
    
    def Count(self):
        return len(self.Meshes)
    
    #def __len__(self):
    #    return sum([len(mesh) for mesh in self.Meshes]) + len(self.BoundingBoxes)
    
    def realignFaces(self):
        #TODO: for each meshpart add vertexsub to each face
        for mesh in self.Meshes:
            for face in mesh.Faces:
                face.adjust(mesh.Header.vertexSub)
    
    def updateCountsOffsets(self):
        vCount = 0
        fCount = 0
        vBufferLen = 0        
        prevVertexSub = 0
        prevBase = 0
        prevBlockSize = 0
        for mesh in self.Meshes:
            mesh.updateCounts()
            vCount,vBufferLen,prevBase,prevVertexSub,prevBlockSize = mesh.updateVertexOffsets(vCount,vBufferLen,prevBase,prevVertexSub,prevBlockSize)
            fCount+=mesh.faceCount()
        self.vertexOffset = len(Mod3Mesh(0,0).Header)*len(self.Meshes) + len(self.BoundingBoxes)
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
        return self.BoundingBoxes.sceneProperties()
    
    def boundingBoxes(self):
        return self.BoundingBoxes.boundingBoxes()
    
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
        self._center = Vector(mod3bb.aabbCenter)
        self._dimensions = Vector((Vector(mod3bb.aabbMax)-Vector(mod3bb.aabbMin))[:3])
        mat = mod3bb.oabbMatrix
        #rows = [[mat[i+4*e] for e in range(4)] for i in range(4)]
        rows = [[mat[4*e+i] for e in range(4)] for i in range(4)]
        self._matrix = Matrix(rows)
        self._vector = Vector(mod3bb.oabbVector[:3])
        self._boneIndex = mod3bb.boneIndex
        self._metadata = {field:getattr(mod3bb,field) for field in Mod3BoundingBox.fields}
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
    

class Mod3BoundingBox(CS.PyCStruct):
    fields = OrderedDict([
            ("boneIndex","int"),
            ("spacer","ubyte[12]"),
            ("aabbCenter","float[3]"),
            ("radius","float"),
            ("aabbMin","float[4]"),
            ("aabbMax","float[4]"),
            ("oabbMatrix","float[16]"),
            ("oabbVector","float[4]"),
            ])
    requiredProperties = { f for f in fields if f != "spacer"}
    defaultProperties = { "spacer":[0xCD]*12}
    def sceneProperties(self):
        return {field:getattr(self,field) for field in self.fields}
    def boundingBox(self):
        return BoundingBox(self)

class Mod3BoundingBoxes(CS.PyCStruct):
    fields = OrderedDict([("count","uint")])
    
    def marshall(self, data):
        super().marshall(data)
        self.BoundingBoxes = [Mod3BoundingBox() for _ in range(self.count)]
        [x.marshall(data) for x in  self.BoundingBoxes]
        
    def construct(self, data):
        data = self.decompose(data)
        self.count = len(data)
        self.BoundingBoxes = [Mod3BoundingBox() for _ in range(self.count)]
        [x.construct(d) for x,d in zip(self.BoundingBoxes,data)]
        return self
    
    def decompose(self,propertyMass):
        return propertyMass
    
    def serialize(self):
        return super().serialize() + b''.join([prop.serialize() for prop in self.BoundingBoxes])
    
    def __len__(self):
        return super().__len__() + sum([len(prop) for prop in self.BoundingBoxes])
    
    def sceneProperties(self):
        properties = {"MeshProperty%05d:%s"%(ix,prop):val for ix, propertyFamily in enumerate(self.BoundingBoxes) for prop,val in propertyFamily.sceneProperties().items()}
        properties["MeshPropertyCount"]=self.count
        return properties
    
    def boundingBoxes(self):
        return [box.boundingBox() for box in self.BoundingBoxes]
    
    def verify(self):
        if self.count == None:
            raise AssertionError("Attribute %s is not initialized."%"count")
        super().verify()
        
    def __iter__(self):
        return iter(self.boundingBoxes())

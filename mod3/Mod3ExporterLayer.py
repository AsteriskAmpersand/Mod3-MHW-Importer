# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 00:15:18 2019

@author: AsteriskAmpersand
"""

try:
    from ..mod3 import Mod3
    from ..mod3 import Mod3VertexBuffers as Mod3Vert
    from ..mod3.Mod3ExporterErrorHandler import ErrorHandler, UnexportableError
except:
    import sys
    sys.path.insert(0, r'..\mod3')
    import Mod3
    import Mod3VertexBuffers as Mod3Vert
    from Mod3ExporterErrorHandler import ErrorHandler, UnexportableError

class WeightCountError(Exception):
    pass
class NegativeWeightError(Exception):
    pass
class UVCountError(Exception):
    pass


class ExporterSettings():
    def __init__(self, api, options):
        self.errorHandler = ErrorHandler(api, options["levels"], options["coerce"])
        self.materialsAdded = False
        self.setHighestLoD = options["lod"]
        self.splitNormals = options["splitnormals"]
        self.exportHidden = options["hidden"]
        self.calculateBoundingBox = options["boundingbox"]
        
    def validateMaterials(self, materials):
        if self.materialsAdded and not materials:
            self.errorHandler.noMaterials()
            materials.append("Dummy_Material")
        for i in range(len(materials)):
            materials[i]={"materialName": materials[i].ljust(128,'\x00')}
    
    def updateMaterials(self, meshprops, materialList):
        self.materialsAdded = True
        if "material" not in meshprops or meshprops["material"] == None:
            idx = 0
        else:
            try:
                idx = materialList.index(meshprops["material"].ljust(128,'\x00'))
            except:
                idx = len(materialList)
                materialList.append(meshprops["material"].ljust(128,'\x00'))
        return idx
    
    def polyfaces(self, face):
        self.errorHandler.polyFace()
        return [{"v1":vert0, "v2":vert1, "v3":vert2} for vert0, vert1, vert2 in zip(face[:-2], face[1:-1], face[2:])]
        
    
    def validateSkeletonRoot(self, rootEmpty):
        if len(rootEmpty)>1:
            self.errorHandler.skeletonRootError("Multiple")
        if not rootEmpty:
            self.errorHandler.skeletonRootError("No")
        return rootEmpty[0]
           
    def executeErrors(self):
        self.errorHandler.verify()

class ModelToMod3():
    def __init__(self, Api, options):
        model = Mod3.Mod3()
        self.model = model
        self.api = Api
        self.options = ExporterSettings(Api, options)
    
    def execute(self, context):
        try:
            fileHeader, groupStuff, trailingData, headerMaterials = self.api.getSceneHeaders(self.options)            
            skeleton,lmatrices,amatrices,bonenames = self.api.getSkeletalStructure(self.options)
            meshparts, materials = self.api.getMeshparts(self.options, bonenames, headerMaterials)
            self.analyzeMeshparts(meshparts)
            self.options.errorHandler.displayErrors()
        except UnexportableError as e:
            self.api.showMessageBox("Export Process failed due to an Error. Check the cause in Window > Toggle_System_Console")
            return
        self.model.construct(fileHeader, materials, groupStuff, skeleton, lmatrices, amatrices, meshparts, trailingData)
        file = open(context,"wb")
        file.write(self.model.serialize())
        file.close()
        
    def analyzeMeshparts(self, meshparts):
        for meshpart in meshparts:
            self.options.errorHandler.setMeshName(meshpart["meshname"])
            meshpart["properties"]["blocktype"] = self.confirmBlockType(meshpart["properties"]["blocktype"], meshpart["mesh"])
            self.compatibilizeMesh(Mod3Vert.Mod3Vertex.blocklist[meshpart["properties"]["blocktype"]], meshpart["mesh"])
        self.options.executeErrors()
        
    
###############################################################################
###############################################################################
###Meshpart Structuring
###############################################################################
###############################################################################
    
    def compatibilizeMesh(self, blockProperties, mesh):
        for vertex in mesh:
            for _ in range(blockProperties["uvs"]-len(vertex["uvs"])):
                vertex["uvs"].append(vertex["uvs"][0])
            vertex["weights"] = vertex["weights"].execute(blockProperties["weights"] if "weights" in blockProperties else 0)
            if "colour" in blockProperties and "colour" not in vertex:
                vertex["colour"]=[0,0,0,255]
        return
            
    def confirmBlockType(self, blocktype, IntermediateVertexList):
        coercion_condition = blocktype in Mod3Vert.Mod3Vertex.blocklist and \
                "weights" in Mod3Vert.Mod3Vertex.blocklist[blocktype] and\
                Mod3Vert.Mod3Vertex.blocklist[blocktype]["weights"]==8
        if coercion_condition:
            temp = self.options.errorHandler.coerce
            self.options.errorHandler.coerce = False                                    
        properties = self.detectVertexProperties(IntermediateVertexList)
        suggestion = self.decideMinimumBlocktype(properties)
        if blocktype is not None:
            compatible = self.blocktypeCompatibility(blocktype, properties)
            if not compatible:
                self.options.errorHandler.blocktypeIncompatible(Mod3Vert.Mod3Vertex.blocklist[suggestion]["name"])
                result = suggestion    
            if compatible:
                result =  blocktype
        else:
            result = suggestion
        if coercion_condition:
            self.options.errorHandler.coerce = temp
        return result
            
    def blocktypeCompatibility(self, blocktype, properties):
        currentProperties = Mod3Vert.Mod3Vertex.blocklist[blocktype]
        for prop in properties:
            if properties[prop]:
                if prop not in currentProperties:
                    return False
                else:
                    if currentProperties[prop]<properties[prop]:
                        return False
        return True
    
    invertedBlocklist = {(val["uvs"],val["weights"] if "weights" in val else 0,val["colour"] if "colour" in val else False):key for key, val in Mod3Vert.Mod3Vertex.blocklist.items()}
    blocklistFields = ["uvs","weights","colour"]
    def decideMinimumBlocktype(self, properties):
        search = (properties["uvs"],properties["weights"],properties["colour"])
        if search not in self.invertedBlocklist:
            self.options.errorHandler.BlocktypeImpossible(search)
        return self.invertedBlocklist[search]
    
    @staticmethod
    def weightDecision(vertexList):
        weightClass = max([vertex["weights"].weightClass() for vertex in vertexList],default = 0)
        return weightClass
    
    @staticmethod
    def uvDecision(vertexList):
        total = len(vertexList[0]["uvs"]) if vertexList else 1
        if total > 4:
            raise UVCountError
        return total
    
    @staticmethod
    def colourDecision(vertexList):
        return any(["colour" in vert for vert in vertexList])
    
    def detectVertexProperties(self,VertexList):
        weightCount = self.weightDecision(VertexList)
        uvs = self.uvDecision(VertexList)
        colour = self.colourDecision(VertexList)
        return {"weights":weightCount, "uvs":uvs, "colour":colour}

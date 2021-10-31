# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 18:22:05 2019

@author: AsteriskAmpersand
"""
import os
try:
    from ..mod3 import Mod3
    from ..mrl3 import Mrl3
    from ..mrl3 import TextureConverter
except:
    import sys
    sys.path.insert(0, r'..\mod3')
    sys.path.insert(0, r'..\mrl3')
    import Mod3
    import Mrl3
    import TextureConverter    

from ..blender.BlenderMod3Importer import BlenderImporterAPI

class CorruptModel(Exception):
    pass

class Mod3ToModel():
    def __init__(self, Mod3File, Api, options):
        model = Mod3.Mod3()
        try:
            model.marshall(Mod3File)
        except:
            raise CorruptModel("Model does not adhere to Mod3 spec. If this file was produced by the previous importer try importing with LOD filtered to highest only.")
        self.model = model
        self.api = Api
        self.calls = self.parseOptions(options)
        
    def execute(self, context):    
        #self.api.resetContext(context)
        for call in self.calls:
            call(context)
            #self.api.resetContext(context)
            
    def parseOptions(self, options):
        execute = []
        if "Clear" in options:
            execute.append(lambda c: self.clearScene(c))
        if "Scene Header" in options:
            execute.append(lambda c: self.setScene(c))
        if "Skeleton" in options:
            skeletonOperator = {"EmptyTree":self.createEmptyTree, 
                        "Armature":self.createArmature}[options["Skeleton"]]
            execute.append(lambda c: skeletonOperator(c))
        if "Only Highest LOD" in options:
            execute.append(lambda c: self.filterToHighestLOD(c))
        if "Mesh Parts" in options:
            execute.append(lambda c: self.createMeshParts(c))
            if "Import Textures" in options:
                execute.append(lambda c: self.importTextures(c, options["Import Textures"]))
            if "Import Materials" in options:
                execute.append(lambda c: self.importMaterials(c, options["Import Materials"]))
        #if "Mesh Unknown Properties" in options:
        #    execute.append(lambda c: self.setMeshProperties(c))
        if "Skeleton" in options and options["Skeleton"] == "Armature":
            execute.append(lambda c: self.linkArmature(c))
        if "Max Clip" in options:
            execute.append(lambda c: self.maximizeClipping(c))
        if "Load Groups and Functions" in options and "Mesh Parts" in options:
            execute.append(lambda c: self.loadGroupsFunctions(c))
        self.splitWeights = {"Group":0, "Split":1, "Slash":2}[options["Split Weights"]]
        self.omitEmpty = "Omit Unused Groups" in options
        self.preserveOrdering = "Preserve Ordering" in options
        return execute
    
    def loadGroupsFunctions(self,c):
        self.api.loadBoundingBoxes(self.model.boundingBoxes(),c)
    
    def overrideMeshDefaults(self, c):
        self.api.overrideMeshDefaults(c)
    
    def setScene(self,c):
        self.api.setScene(self.model.sceneProperties(),c)
        
    def setMeshProperties(self,c):
        self.api.setMeshProperties(self.model.meshProperties(),c)
    
    def createEmptyTree(self, c):
        self.api.createEmptyTree(self.model.prepareArmature(),self.preserveOrdering,c)
    
    def createArmature(self,c):
        self.api.createArmature(self.model.prepareArmature(),c)
        
    def createMeshParts(self,c):
        self.api.createMeshParts(self.model.prepareMeshparts(self.splitWeights),self.omitEmpty,c)
        
    def clearScene(self,c):
        self.api.clearScene(c)
        
    def maximizeClipping(self,c):
        self.api.maximizeClipping(c)

    def linkEmptyTree(self,c):
        self.api.linkEmptyTree(c)
        
    def linkArmature(self,c):
        self.api.linkArmature(c)
    
    def loadMaterial(self,matPath):
        self.material = Mrl3.MRL3()
        materialPath = matPath[:-5]+".mrl3"
        try:
            materialFile = open(materialPath,"rb")
        except:
            BlenderImporterAPI.dbg.write("\tNo MRL3 found in model directory")
            raise
        try:
            self.material.marshall(materialFile)
        except Exception as e:
            BlenderImporterAPI.dbg.write("\tUnable to read corrupted MRL3.")
            BlenderImporterAPI.dbg.write("\t\t%s."%str(e))
            print(str(e))
            raise
    
    def importTextures(self,c,chunkpath):
        try:
            self.loadMaterial(c.path)
        except:
            return
        self.api.importTextures(lambda skinHash: materialPathForkingResolution(c.path, self.material[skinHash], chunkpath),c)
    
    def importMaterials(self,c,chunkpath):
        try:
            self.loadMaterial(c.path)
        except:
            return
        self.api.importMaterials(lambda skinHash, matType: materialPathForkingResolution(c.path, self.material.getMaterial(skinHash,matType), chunkpath),c)
        
        
    def filterToHighestLOD(self,c):
        self.model.filterLOD()
        return

###############################################################################
###############################################################################
###Material Structuring
###############################################################################
###############################################################################

def materialPathForkingResolution(modelPath, texturePath, chunkPath):
    BlenderImporterAPI.dbg.write("\tModel Path: %s\n"%modelPath)
    BlenderImporterAPI.dbg.write("\tTexture Path: %s\n"%texturePath)
    BlenderImporterAPI.dbg.write("\tChunk Path: %s\n"%chunkPath)
    filename = os.path.basename(texturePath)
    modelFolder = os.path.dirname(os.path.abspath(modelPath))
    pathCandidates = [os.path.join(chunkPath,texturePath), os.path.join(modelFolder,filename)]
    for path in pathCandidates:
        BlenderImporterAPI.dbg.write("\tAttempting: %s\n"%path)
        if os.path.exists(path+".PNG"):
            return path
        elif os.path.exists(path+".dds"):
            TextureConverter.convertDDSToPNG(path+".dds")
            return path
        elif os.path.exists(path+".tex"):
            TextureConverter.convertTexToDDS(path+".tex")
            TextureConverter.convertDDSToPNG(path+".dds")
            return path
    return 
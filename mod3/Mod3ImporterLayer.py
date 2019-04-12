# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 18:22:05 2019

@author: AsteriskAmpersand
"""
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
        excecute = []
        if "Clear" in options:
            excecute.append(lambda c: self.clearScene(c))
        if "Scene Header" in options:
            excecute.append(lambda c: self.setScene(c))
        if "Armature" in options:
            excecute.append(lambda c: self.createArmature(c))
        if "Only Highest LOD" in options:
            excecute.append(lambda c: self.filterToHighestLOD(c))
        if "Mesh Parts" in options:
            if "Split Weights" in options:
                self.splitWeights = True
            else:
                self.splitWeights = False
            excecute.append(lambda c: self.createMeshParts(c))
            if "Import Textures" in options:
                excecute.append(lambda c: self.importTextures(c, options["Import Textures"]))
        if "Mesh Unknown Properties" in options:
            excecute.append(lambda c: self.setMeshProperties(c))
        if "Skeleton Modifier" in options:
            excecute.append(lambda c: self.linkArmatureMesh(c))
        if "Max Clip" in options:
            excecute.append(lambda c: self.maximizeClipping(c))
        #Max clipping distance?
        return excecute
    
    def setScene(self,c):
        self.api.setScene(self.model.sceneProperties(),c)
        
    def setMeshProperties(self,c):
        self.api.setMeshProperties(self.model.meshProperties(),c)
    
    def createArmature(self,c):
        self.api.createArmature(self.model.prepareArmature(),c)
        
    def createMeshParts(self,c):
        self.api.createMeshParts(self.model.prepareMeshparts(self.splitWeights),c)
        
    def clearScene(self,c):
        self.api.clearScene(c)
        
    def maximizeClipping(self,c):
        self.api.maximizeClipping(c)
        
    def linkArmatureMesh(self,c):
        self.api.linkArmatureMesh(c)
        
    def importTextures(self,c,chunkpath):
        self.material = Mrl3.MRL3()
        materialPath = c.path[:-5]+".mrl3"
        try:
            materialFile = open(materialPath,"rb")
        except:
            print("No MRL3 found in model directory")
            return
        try:
            self.material.marshall(materialFile)
        except Exception as e:
            print("Unable to read corrupted MRL3")
            print(str(e))
            return
        self.api.importTextures(lambda skinHash: materialPathForkingResolution(c.path, self.material[skinHash], chunkpath),c)        
        
        
    def filterToHighestLOD(self,c):
        self.model.filterLOD()
        return

###############################################################################
###############################################################################
###Material Structuring
###############################################################################
###############################################################################
import os

def materialPathForkingResolution(modelPath, texturePath, chunkPath):
    filename = os.path.basename(texturePath)
    modelFolder = os.path.dirname(os.path.abspath(modelPath))
    pathCandidates = [os.path.join(modelFolder,filename), os.path.join(chunkPath,texturePath)]
    for path in pathCandidates:
        if os.path.exists(path+".png"):
            return path
        elif os.path.exists(path+".dds"):
            TextureConverter.convertDDSToPNG(path+".dds")
            return path
        elif os.path.exists(path+".tex"):
            TextureConverter.convertTexToDDS(path+".tex")
            TextureConverter.convertDDSToPNG(path+".dds")
            return path
    return 
    #TODO - Here be Dragons
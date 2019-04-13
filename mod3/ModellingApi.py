# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 00:21:26 2019

@author: AsteriskAmpersand
"""
class debugger():
    def __init__(self, 
                 path = r"C:\Users\AsteriskAmpersand\AppData\Roaming\Blender Foundation\Blender\2.79\scripts\addons\CleanModelImporter\dbg.txt",
                 debug = False):
        self.debug = debug
        if self.debug:
            self.dbgFile = path
            self.dbg = open(path, "w", buffering = 1)
        return
    
    def write(self, text):
        if self.debug:
            self.dbg.write(text)
            self.dbg.close()
            self.dbg = open(self.dbgFile, "a", buffering = 1)
        
class ModellingAPI():   
    MeshDefaults = ["boneremapid","material","unkn","unkn2","unkn3","unkn9","visibleCondition"]
    
    def setScene(self, scene_properties, c):
        raise NotImplemented

    def createArmature(self, armature, c):
        raise NotImplemented
        
    def createMeshParts(self, meshPartList, c):
        raise NotImplemented
        
    def importTextures(self, importerFunction, c):
        raise NotImplemented
        
    def clearScene(self, c):
        raise NotImplemented
        
    def getSceneHeaders(self, options):
        raise NotImplemented
        
    def getSkeletalStructure(self, options):
        raise NotImplemented
        
    def getMeshparts(self, options):
        raise NotImplemented
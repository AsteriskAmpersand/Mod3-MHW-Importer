# -*- coding: utf-8 -*-
"""
Created on Thu Mar 28 22:15:37 2019

@author: AsteriskAmpersand
"""

from collections import Counter, OrderedDict

class UnhandledErrors(Exception):
    pass
class UnexportableError(Exception):
    pass


class ErrorHandler():
    def __init__(self, api, propertyLevels, coerce):
        self.MessageList = None
        self.PermanentRecord = OrderedDict()
        self.meshname = None
        self.section = None
        self.Error = False
        self.Warning = False
        self.Ignore = False
        self.api = api
        self.coerce = coerce
        for prop in propertyLevels:
            self.__setattr__(prop,propertyLevels[prop])
        
    def displayErrors(self):
        self.stowErrors()
        separator = "==================================\n"
        message = ""
        for section, errors in self.PermanentRecord.items():
            if errors:
                message+='\n'+separator+section+'\n'+separator+'\n'.join(errors)+'\n'
        self.api.displayErrors(message)
        return        
        
    def stowErrors(self):
        c = Counter(self.MessageList)
        if self.section not in self.PermanentRecord:
            self.PermanentRecord[self.section] = []
        self.PermanentRecord[self.section] += ["%d instance%s of:\n%s"%(c[entry],"s" if c[entry]>1 else "" , entry) for entry in sorted(c.keys())]
        self.MessageList = []
        
    def verify(self):
        self.stowErrors()
        if self.Error:
            self.displayErrors()
            raise UnexportableError("Aborting exporting process, an unignorable error was found. Please review the errors and warnings logs. (Window > Toggle System Console)")
        self.Warning = False
        self.Error = False
        
    def setMeshName(self, meshname):
        self.meshname = meshname
        self.normalOffenders = {}
        self.uvOffenders = {}
        self.colourOffenders = {}

    def setSection(self, sectionName):
        if self.MessageList:
            self.displayErrors()
            raise UnhandledErrors("""Unhandled Error Log when switching sections. Something has gone terribly wrong, contact *&#7932 on Discord, AsteriskAmpersand on Github or NexusMods. This error shouldn't be visible under normal operation.""")
        self.meshname = None
        self.section = sectionName
        self.MessageList = []

    def BlocktypeImpossible(self, requirements):
        self.Error = True
        self.MessageList.append((self.meshname, 
                """Error: Properties combination are not compatible with any of Capcom blocktypes. UV:%d, Weights:%d, Colour:%d"""%(requirements))
                )
        self.verify()
    def blocktypeIncompatible(self, sugestion):
        self.__setattr__(self.blocktypeLevel,True)
        if self.blocktypeLevel != "Ignore":
            self.MessageList.append((self.meshname, 
                    """%s: Declared blocklabel is incompatible with mesh. Lower blocktype errors to warning to allow overwriting explicit blocklabels, remove blocklabel from mesh properties or set blocklabel to %s"""%(self.blocktypeLevel, sugestion)
                    ))
    def vertexCountOverflow(self):
        self.Error = True
        self.MessageList.append((self.meshname,
                """Error: Vertex Count exceeds hard coded limit of 65535 vertices."""
                ))
    def faceCountOverflow(self):
        self.Error = True
        self.MessageList.append((self.meshname,
                """Error: Face Count exceeds hard coded limit of 4294967295 faces."""
                ))
    def propertyDuplicate(self, propertyName, storage, prop):
        self.__setattr__(self.propertyLevel,True)
        if self.propertyLevel != "Ignore":
            message = "%s: Duplicated property %s" % (self.propertyLevel, propertyName)
            if self.section == "Meshes":
                message = (self.meshname,message)
            self.MessageList.append(message)
        
        
    propertyDefaults = {"boneFunction":512, "child":255,
                        "MeshProperty":[0]*36,
                        "GroupProperty":0,
                        "MeshPropertyCount":0, "boneMapCount":0xFFFFFFF,
                        "groupCount":0,"vertexIds":0xFFFF, "materialCount":0,
                        "unkn":0,"unkn1":0,"unkn2":0,"unkn3":0,"unkn9":[0]*39,
                        "hUnkn1":[0]*38, "hUnkn2":[0]*64,
                        "TrailingData":[], "material":None,
                        "visibleCondition":0,"lod":0xFFFF,"blockLabel":None,
                        "boneremapid":0,    
                        }
    def attemptLoadDefaults(self, defaults, source):
        for prop in defaults:
            if "DefaultMesh-"+prop in source:
                self.propertyDefaults[prop]=source["DefaultMesh-"+prop]
        return
        
    def propertyMissing(self, propertyName):
        if "MeshProperty" in propertyName and "Count" not in propertyName:
            propertyName = "MeshProperty"
        if "GroupProperty" in propertyName and "Count" not in propertyName:
            propertyName = "GroupProperty"
        self.__setattr__(self.propertyLevel,True)
        if self.propertyLevel != "Ignore":
            message = "%s: Missing Property %s, defaults to %s"%(self.propertyLevel, propertyName, str(self.propertyDefaults[propertyName]))
            if self.section == "Meshes":
                message = (self.meshname,message)
            self.MessageList.append(message)
        return self.propertyDefaults[propertyName]
    
    defaultLoops = {"normal":(0.0,0.0,0.0),
                    "tangent":(0,0,0,127),
                    "colour":(0,0,0,255)
                }
    
    def verifyLoadLoop(self, field, customVert, blenderVert, loopArray, mesh):
        if blenderVert.index not in loopArray:
            self.__setattr__(self.loopLevel,True)
            if self.loopLevel != "Ignore":
                self.MessageList.append((self.meshname,"%s: Missing %s at vertex implies orphan vertex or no UV to generate normals."%(self.loopLevel, field)))
            customVert[field]=self.defaultLoops[field]
        else:
            customVert[field] = loopArray[blenderVert.index]
    
    def missingUV(self, vix, uvMap):
        self.__setattr__(self.uvLevel,True)
        if self.uvLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: Missing UV at vertex implies orphan vertex or corrupted UV Map."%self.uvLevel))
        return [0.0,0.0]
    
    def uvLayersMissing(self, vert):
        self.Error = True
        self.MessageList.append((self.meshname,"Error: Missing UV Maps."))
        vert["uvs"] = [[0.0,0.0]]
        return
    
    def uvCountExceeded(self, vert):
        self.__setattr__(self.uvLevel,True)
        if self.uvLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: More than 4 UV Maps."%self.uvLevel))
        vert["uvs"] = vert["uvs"][:4]
        return
    
    def excessColorLayers(self, colourLayers):
        self.__setattr__(self.colourLevel,True)
        if self.colourLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: More than 1 Colour Maps."%self.colourLevel))
        return colourLayers[0].data
    
    def duplicateNormal(self, loopIx, vNormal, vTangent, normals):
        self.__setattr__(self.loopLevel,True)
        if self.loopLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: Multiple different normals per face at single vertex. Consider editing custom split normals or using blender's default normals."%self.loopLevel))
        if loopIx not in self.normalOffenders:
            self.normalOffenders[loopIx] = []
        self.normalOffenders[loopIx].append((vNormal,vTangent))
        #if necessary the code can be made more complex to handle this case more elegantly for now it just keeps only the first
        
    def duplicateUV(self, loop, loopUV, uvMap):
        self.__setattr__(self.uvLevel,True)
        if self.uvLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: Multiple different uvs per loop at single vertex. Consider marking islands as seams and then splitting at seams."%self.uvLevel))
        if loop.vertex_index not in self.uvOffenders:
            self.uvOffenders[loop.vertex_index] = []
        self.uvOffenders[loop.vertex_index].append(loopUV)
        #if necessary the code can be made more complex to handle this case more elegantly for now it just keeps only the first    
    
    @staticmethod
    def colourMean(colorArray):
        return list(map(round,sum(colorArray,colorArray[0]*0)/len(colorArray)))
    
    def duplicateColor(self, vertIndex, color, vertColor):
        self.__setattr__(self.colourLevel,True)
        if self.colourLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: Multiple different colours per loop at single vertex."%self.colourLevel))
        if vertIndex not in self.colourOffenders:
            self.colourOffenders[vertIndex] = []
        self.colourOffenders[vertIndex].append(color)
        vertColor[vertIndex]=list(self.colourMean(self.colourOffenders[vertIndex]))
        #if necessary the code can be made more complex to handle this case more elegantly for now it just keeps only the first 

    def uninversibleBlockLabel(self):
        self.__setattr__(self.blocktypeLevel,True)
        if self.blocktypeLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: Illegal blocklabel. It's been nulled and will be directly calcualted from the mesh instead."%self.blocktypeLevel))

    def invalidGroupName(self, weightName):
        self.__setattr__(self.weightLevel,True)
        if self.blocktypeLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: Weight group %s not associated to any bone, consider deleting."%(self.weightLevel, weightName)))

    def polyFace(self):
        self.Error = True
        self.MessageList.append((self.meshname,"Error: Non triangular face. Run Blender's triangulation previous to export."))
        self.verify()
        
    def multipleNegativeWeights(self, weights):
        self.__setattr__(self.weightCountLevel,True)
        if self.weightCountLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: Multiple Negatives Weights on a single vertex."%(self.weightCountLevel)))
        return [sorted(weights, key=lambda x: x.weight)[0]]

    def weightCountExceeded(self, bufferedWeights):
        self.__setattr__(self.weightCountLevel,True)
        if self.weightCountLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: Vertex is weighted to more than 8 weights."%(self.weightCountLevel)))
        bufferedWeights.unsigned = sorted(bufferedWeights.unsigned, key = lambda x: 1 if x.boneId == 0 and not x.weight else -x.weight)
        if not bufferedWeights.signed:
            bufferedWeights.signed = [bufferedWeights.unsigned[-1]]
        bufferedWeights.unsigned = bufferedWeights.unsigned[:7]
        
    def negativeWeightPrecision(self, bufferedWeights, count):
        self.__setattr__(self.weightCountLevel,True)
        if self.weightCountLevel != "Ignore":
            self.MessageList.append((self.meshname,"%s: Vertex is weighted to %d weights with no explicit negative."%(self.weightCountLevel, count))) 
        bufferedWeights.unsigned = sorted(bufferedWeights.unsigned, key = lambda x: 1 if x.boneId == 0 and not x.weight else -x.weight)
        bufferedWeights.signed = [bufferedWeights.unsigned[-1]]
        bufferedWeights.unsigned = bufferedWeights.unsigned[:(count-1)]
        
    def noMaterials(self):
        self.stowErrors()
        self.Warning = True        
        self.MessageList.append("Warning: No materials on any mesh or in header, and at least 1 mesh exists. Ensure there are no meshes or at least one of them has a material property.")
        self.verify()
        
    def skeletonRootError(self, quantifier):
        self.Error = True
        self.MessageList.append("Error: %s candidate empty roots for the skeleton."%quantifier)
        self.verify()
<<<<<<< HEAD
        
    def testGroupFunction(self, groupNameFunction, groupID):
        try:
            groupNameFunction(groupID)
            return True
        except:
            return False
=======
>>>>>>> origin/master

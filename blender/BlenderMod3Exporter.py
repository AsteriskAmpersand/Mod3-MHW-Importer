# -*- coding: utf-8 -*-
"""
Created on Sun Mar 31 03:16:11 2019

@author: AsteriskAmpersand
"""


import bpy
import math
from mathutils import Matrix
from collections import OrderedDict
   
try:
    from ..mod3.ModellingApi import ModellingAPI, debugger
    from ..mod3.Mod3DelayedResolutionWeights import BufferedWeight, BufferedWeights
    from ..mod3.Mod3VertexBuffers import Mod3Vertex
    from ..common.crc import CrcJamcrc
except:
    import sys
    sys.path.insert(0, r'..\mod3')
    sys.path.insert(0, r'..\common')
    from Mod3DelayedResolutionWeights import BufferedWeight, BufferedWeights
    from Mod3VertexBuffer import Mod3Vertex
    from ModellingApi import ModellingAPI, debugger
    from crc import CrcJamcrc
    
generalhash =  lambda x:  CrcJamcrc.calc(x.encode())
    
import re
class BlenderExporterAPI(ModellingAPI):
    MACHINE_EPSILON = 2**-19
    dbg = debugger()

    class SettingsError(Exception):
        pass

    @staticmethod
    def showMessageBox(message = "", title = "Message Box", icon = 'INFO'):
    
        def draw(self, context):
            self.layout.label(message)
    
        bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)
    
    @staticmethod
    def displayErrors(errors):
        if errors:
            print(errors)
            BlenderExporterAPI.showMessageBox("Warnings have been Raised, check them in Window > Toggle_System_Console", title = "Warnings and Error Log")
# =============================================================================
# Main Exporter Calls
# =============================================================================

    @staticmethod
    def getSceneHeaders(options):
        header = {}
        trail = {}
        options.errorHandler.setSection("Scene Headers")
        BlenderExporterAPI.verifyLoad(bpy.context.scene,"TrailingData",options.errorHandler,trail)
        for prop in ["MeshPropertyCount", "boneMapCount", "groupCount", "materialCount","vertexIds", "unkn1", "unkn2"]:
            BlenderExporterAPI.verifyLoad(bpy.context.scene,prop,options.errorHandler,header)
        meshProps = OrderedDict()
        for ix in range(header["MeshPropertyCount"]):
            BlenderExporterAPI.verifyLoad(bpy.context.scene,"MeshProperty%d"%ix,options.errorHandler,meshProps)
        materials = OrderedDict()
        for ix in range(header["materialCount"]):
            BlenderExporterAPI.verifyLoad(bpy.context.scene,"MaterialName%d"%ix,options.errorHandler,materials)
        groupProperties = OrderedDict()
        for ix in range(8*header["groupCount"]):
            BlenderExporterAPI.verifyLoad(bpy.context.scene,"GroupProperty%d"%ix,options.errorHandler,groupProperties)
        options.executeErrors()
        #bpy.context.scene
        return header, list(meshProps.values()), list(groupProperties.values()), trail["TrailingData"], list(materials.values())
        
    @staticmethod
    def getSkeletalStructure(options):
        skeletonMap = {}
        options.errorHandler.setSection("Skeleton")
        rootEmpty = [o for o in bpy.context.scene.objects if o.type =="EMPTY" and not o.parent]
        root = options.validateSkeletonRoot(rootEmpty)
        protoskeleton = []
        BlenderExporterAPI.recursiveEmptyDeconstruct(255, root, protoskeleton, skeletonMap, options.errorHandler)
        for bone in protoskeleton: bone["bone"]["child"] = skeletonMap[bone["bone"]["child"]] if bone["bone"]["child"] in skeletonMap else 255
        options.executeErrors()
        return [bone["bone"] for bone in protoskeleton], \
                [bone["LMatrix"] for bone in protoskeleton], \
                [bone["AMatrix"] for bone in protoskeleton], \
                skeletonMap
        
    @staticmethod
    def getMeshparts(options, boneNames, materials):
        options.errorHandler.setSection("Meshes")
        options.errorHandler.attemptLoadDefaults(ModellingAPI.MeshDefaults, bpy.context.scene)
        meshes = sorted([o for o in bpy.context.scene.objects if o.type=="MESH"], key=lambda x: x.data.name)
        meshlist = [BlenderExporterAPI.parseMesh(mesh,materials,boneNames,options) for mesh in meshes]
        options.validateMaterials(materials)
        options.executeErrors()
        return meshlist, materials
    
# =============================================================================
# Exporter Functions:
# =============================================================================
    @staticmethod
    def verifyLoad(source, propertyName, errorHandler, storage):
        if propertyName in source:
            prop = source[propertyName]
        else:
            prop = errorHandler.propertyMissing(propertyName)
        if propertyName in storage:
            errorHandler.propertyDuplicate(propertyName, storage, prop)
        else:
            storage[propertyName]=prop
        return
    
    @staticmethod
    def recursiveEmptyDeconstruct(pix, current, storage, skeletonMap, errorHandler):
        for child in current.children:
            bone = {"name":child.name}
            for prop in ["boneFunction","unkn2"]:
                BlenderExporterAPI.verifyLoad(child, prop, errorHandler, bone)
            #Check Child Constraint
            bone["child"] = BlenderExporterAPI.getTarget(child, errorHandler)
            LMatrix= child.matrix_local.copy()
            AMatrix= LMatrix.inverted()*(storage[pix]["AMatrix"] if len(storage) and pix != 255  else Matrix.Identity(4))
            bone["x"], bone["y"], bone["z"] = (LMatrix[i][3] for i in range(3))
            bone["parentId"] = pix
            bone["length"]=math.sqrt(bone["x"]**2 +bone["y"]**2+ bone["z"]**2)
            cix = len(storage)
            storage.append({"bone":bone,"AMatrix":AMatrix,"LMatrix":LMatrix})
            skeletonMap[child.name] = cix
            BlenderExporterAPI.recursiveEmptyDeconstruct(cix, child, storage, skeletonMap, errorHandler)
       
    @staticmethod
    def getTarget(bone, errorHandler):
        constraints = [b for b in bone.constraints if b.type == "CHILD_OF"]
        if not len(constraints):
            return None
        constraint = constraints[0]
        if len(constraints)>1:
            bone["child"]=constraint
            for c in constraints[1:]:
                errorHandler.propertyDuplicate("child",bone,c)
            constraint = bone["child"]
        return constraint.target.name if constraint.target else bone.name
        
    
    @staticmethod
    def parseMesh(mesh, materials, skeletonMap, options):
        options.errorHandler.setMeshName(mesh.name)
        meshProp = {}
        if options.setHighestLoD:
            mesh.data["lod"] = 0xFFFF
        for prop in ["unkn","visibleCondition","lod","unkn2","unkn3","blockLabel",
                    "boneremapid","unkn9", "material"]  :
            BlenderExporterAPI.verifyLoad(mesh.data, prop, options.errorHandler, meshProp)
        meshProp["blocktype"] = BlenderExporterAPI.invertBlockLabel(meshProp["blockLabel"], options.errorHandler)
        groupName = lambda x: mesh.vertex_groups[x].name
        loopNormals, loopTangents = BlenderExporterAPI.loopValues(mesh.data, options.splitNormals, options.errorHandler)
        uvMaps = BlenderExporterAPI.uvValues(mesh.data, options.errorHandler)
        colour = BlenderExporterAPI.colourValues(mesh, options.errorHandler)
        pymesh = []
        if len(mesh.data.vertices)>65535:
            options.errorHandler.vertexCountOverflow()
        for vertex in mesh.data.vertices:
            vert = {}
            vert["position"] = vertex.co
            vert["weights"] = BlenderExporterAPI.weightHandling(vertex.groups, skeletonMap, groupName, options.errorHandler)
            #Normal Handling
            options.errorHandler.verifyLoadLoop("normal", vert, vertex, loopNormals, mesh)#vert["normal"] = loopNormals[vertex.index]
            #Tangent Handling
            options.errorHandler.verifyLoadLoop("tangent", vert, vertex, loopTangents, mesh)#vert["tangent"] = loopTangents[vertex.index]
            #UV Handling
            vert["uvs"] = [uvMap[vertex.index] if vertex.index in uvMap else options.errorHandler.missingUV(vertex.index, uvMap) for uvMap in uvMaps]
            if not len(vert["uvs"]):
                options.errorHandler.uvLayersMissing(vert)            
            if len(vert["uvs"])>4:
                options.errorHandler.uvCountExceeded(vert)
            #Colour Handling if present
            if colour:
                options.errorHandler.verifyLoadLoop("colour", vert, vertex, colour, mesh)
            pymesh.append(vert)
        faces = []
        for face in mesh.data.polygons:
            if len(face.vertices)>3:
                faces += options.polyfaces(face)
            else:
                faces.append({v:vert for v,vert in zip(["v1","v2","v3"],face.vertices)})
        if len(faces)>4294967295:
            options.errorHandler.faceCountOverflow()
        meshProp["materialIdx"] = options.updateMaterials(meshProp,materials)
        return {"mesh":pymesh, "faces":faces, "properties":meshProp, "meshname":mesh.name}
    
    @staticmethod
    def invertBlockLabel(blockLabel, errorHandler):
        blockhash = generalhash(blockLabel) if blockLabel else None
        if blockhash and blockhash not in Mod3Vertex.blocklist:
            blockhash = errorHandler.uninversibleBlockLabel()  
        return blockhash
    
    @staticmethod
    def loopValues(mesh, useSplit, errorHandler):
        if not useSplit or not mesh.use_auto_smooth:
            mesh.use_auto_smooth = True
            mesh.normals_split_custom_set_from_vertices([vert.normal for vert in mesh.vertices])
        try:
            mesh.calc_tangents()
        except:
            pass
        normals = {}
        tangents = {}
        for loop in mesh.loops:
            vNormal = list(map(round,loop.normal*127))+[0]
            vTangent = list(map(round, loop.tangent*127)) + [int(loop.bitangent_sign)*127]
            if loop.vertex_index in normals and \
                any([not (-1<=(c0-c1)<=1) for c0,c1 in zip(normals[loop.vertex_index],vNormal) ]):
                bpy.context.scene.cursor_location = mesh.vertices[loop.vertex_index].co
                errorHandler.duplicateNormal(loop.vertex_index, vNormal, vTangent, normals)
            else:
                normals[loop.vertex_index] = vNormal
                tangents[loop.vertex_index] = vTangent
        return normals, tangents
    
    @staticmethod    
    def uvValues(mesh, errorHandler):
        uvList = []
        for layer in mesh.uv_layers:
            uvMap = {}
            for loop,loopUV in zip(mesh.loops, layer.data): #.uv
                uvPoint = (loopUV.uv[0],1-loopUV.uv[1])
                if loop.vertex_index in uvMap and uvMap[loop.vertex_index] != uvPoint:
                    errorHandler.duplicateUV(loop, loopUV.uv, uvMap)
                else:
                    uvMap[loop.vertex_index] = uvPoint
            uvList.append(uvMap)
        return uvList#int(bitangent_sign)*127
    
    @staticmethod
    def colourValues(mesh, errorHandler):
        if len(mesh.data.vertex_colors)==0:
            return None
        if len(mesh.data.vertex_colors)>1:
            colorLayer = errorHandler.excessColorLayers(mesh.data.vertex_colors)
        else:
            colorLayer = mesh.data.vertex_colors[0].data
        vertColor = {}
        for loop, colorLoop in zip(mesh.data.loops, colorLayer):
            color = list(map(int,colorLoop.color*255))+[255]
            vertIndex = loop.vertex_index
            if vertIndex in vertColor and color != vertColor[vertIndex]:
                errorHandler.duplicateColor(vertIndex, color, vertColor)
            else:
                vertColor[vertIndex]=color
        return vertColor
    

    @staticmethod    
    def weightHandling(weightGroups, skeletonMap, groupNameFunction, errorHandler):
        parsedGroups = [(groupNameFunction(group.group), group.weight) for group in weightGroups]
        validGroupName = lambda w: BlenderExporterAPI.validGroupName(w, skeletonMap, errorHandler)
        weights = BufferedWeights([BufferedWeight(weightName,skeletonMap,weightVal) for weightName, weightVal in parsedGroups if validGroupName(weightName)],errorHandler)
        return weights
        #Handle Cases    
        #            preliminaryGroups = [(groupName(group.group),group.weight) for group in vertex.groups if BlenderExporterAPI.validGroupName(groupName(group.group), skeletonMap, options.errorHandler)]
        #     = BlenderExporterAPI.weightReorganize(preliminaryGroups, skeletonMap, options.errorHandler)
        
        
    weightCaptureGroup = BufferedWeight.weightCaptureGroup  
    @staticmethod
    def validGroupName(weightName, skeletonNames, errorHandler):
        if weightName in skeletonNames:
            return True
        match = re.match(BlenderExporterAPI.weightCaptureGroup,weightName)
        if match and match.group(1)+match.group(2) in skeletonNames:
            return True
        else:
            errorHandler.invalidGroupName(match.group(1)+match.group(2) if match else weightName)
            return False
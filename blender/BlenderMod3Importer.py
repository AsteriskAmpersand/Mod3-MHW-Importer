# -*- coding: utf-8 -*-
"""
Created on Sun Mar 31 03:11:30 2019

@author: AsteriskAmpersand
"""

import bpy
import bmesh
import array
import os
from mathutils import Vector, Matrix
from collections import OrderedDict
try:
    from ..mod3.ModellingApi import ModellingAPI, debugger
except:
    import sys
    sys.path.insert(0, r'..\mod3')
    from ModellingApi import ModellingAPI, debugger
    
def processPath(path):
    return os.path.splitext(os.path.basename(path))[0]
    
class BlenderImporterAPI(ModellingAPI):
    MACHINE_EPSILON = 2**-19
    dbg = debugger()
    
#=============================================================================
# Main Importer Calls
# =============================================================================
       
    @staticmethod
    def setScene(scene_properties, context):
        BlenderImporterAPI.parseProperties(scene_properties,bpy.context.scene.__setitem__)
    
    @staticmethod   
    def setMeshProperties(meshProperties, context):
        BlenderImporterAPI.parseProperties(meshProperties,bpy.context.scene.__setitem__)
      
    @staticmethod
    def createArmature(armature, context):
        miniscene = OrderedDict()
        BlenderImporterAPI.createRootNub(miniscene)
        for ix, bone in enumerate(armature):
            if "Bone.%03d"%ix not in miniscene:
                BlenderImporterAPI.createNub(ix, bone, armature, miniscene)
        miniscene["Bone.%03d"%255].name = '%s Armature'%processPath(context.path)
        BlenderImporterAPI.linkChildren(miniscene)
        context.armature = miniscene
        return
        
    @staticmethod
    def createSkeleton(armature, context):#Skeleton
        filename = processPath(context.path)
        BlenderImporterAPI.dbg.write("Loading Armature\n")
        bpy.ops.object.select_all(action='DESELECT')
        blenderArmature = bpy.data.armatures.new('%s Armature'%filename)
        arm_ob = bpy.data.objects.new('%s Armature'%filename, blenderArmature)
        bpy.context.scene.objects.link(arm_ob)
        bpy.context.scene.update()
        arm_ob.select = True
        arm_ob.show_x_ray = True
        bpy.context.scene.objects.active = arm_ob
        
        blenderArmature.draw_type = 'STICK'
        bpy.ops.object.mode_set(mode='EDIT')
        for ix, bone in enumerate(armature):
            if "Bone.%03d"%ix not in blenderArmature:
                BlenderImporterAPI.createBone(ix, bone, armature, blenderArmature)
            #arm.pose.bones[ix].matrix
        bpy.ops.object.editmode_toggle()
        BlenderImporterAPI.dbg.write("Loaded Armature\n")
        context.armature = arm_ob
        return
    
    @staticmethod
    def createMeshParts(meshPartList, context):
        meshObjects = []
        filename = processPath(context.path)
        bpy.ops.object.select_all(action='DESELECT')
        BlenderImporterAPI.dbg.write("Creating Meshparts\n")
        #blenderMeshparts = []
        for ix, meshpart in enumerate(meshPartList):
            BlenderImporterAPI.dbg.write("\tLoading Meshpart %d\n"%ix)
            #Geometry
            BlenderImporterAPI.dbg.write("\tLoading Geometry\n")
            blenderMesh, blenderObject = BlenderImporterAPI.createMesh("%s %03d"%(filename,ix),meshpart)
            BlenderImporterAPI.parseProperties(meshpart["properties"], blenderMesh.__setitem__)
            BlenderImporterAPI.dbg.write("\tBasic Face Count %d\n"%len(meshpart["faces"]))
            #Weight Handling
            BlenderImporterAPI.dbg.write("\tLoading Weights\n")
            BlenderImporterAPI.writeWeights(blenderObject, meshpart)
            #Normals Handling
            BlenderImporterAPI.dbg.write("\tLoading Normals\n")
            BlenderImporterAPI.setNormals(meshpart["normals"],blenderMesh)
            #Colour
            #Needs to enter object mode
            if meshpart["colour"]:
                BlenderImporterAPI.dbg.write("\tLoading Colours\n")
                vcol_layer = blenderMesh.vertex_colors.new()
                for l,col in zip(blenderMesh.loops, vcol_layer.data):
                    col.color = BlenderImporterAPI.mod3ToBlenderColour(meshpart["colour"][l.vertex_index])[:3]
            #UVs
            BlenderImporterAPI.dbg.write("\tLoading UVs\n")
            for ix, uv_layer in enumerate(meshpart["uvs"]):
                uvLayer = BlenderImporterAPI.createTextureLayer("UV%d"%ix, blenderMesh, uv_layer)#BlenderImporterAPI.uvFaceCombination(uv_layer, meshpart["faces"]))
                uvLayer.active = ix == 0
                BlenderImporterAPI.dbg.write("\tLayer Activated\n")
            BlenderImporterAPI.dbg.write("\tMeshpart Loaded\n")
            blenderMesh.update()
            meshObjects.append(blenderObject)
        context.meshes = meshObjects
        if meshObjects and context.setDefaults:
            BlenderImporterAPI.setWorldMeshDefault((meshObjects[0].data))
        BlenderImporterAPI.dbg.write("Meshparts Created\n")
        
    @staticmethod
    def linkArmatureMesh(context):
        return
        armature = context.armature
        for ob in context.meshes:
            ob.modifiers.new(name = armature.name, type='ARMATURE')
            ob.modifiers[armature.name].object = armature
        
    @staticmethod
    def clearScene(context):
        BlenderImporterAPI.dbg.write("Clearing Scene\n")
        for key in list(bpy.context.scene.keys()):
            del bpy.context.scene[key]
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete() 
        for i in bpy.data.images.keys():
            bpy.data.images.remove(bpy.data.images[i])
        BlenderImporterAPI.dbg.write("Scene Cleared\n")
        return
    
    @staticmethod
    def importTextures(textureFetch, context):
        BlenderImporterAPI.dbg.write("Importing Texture\n")
        if not textureFetch:
            BlenderImporterAPI.dbg.write("Failed to Import Texture\n")
            return
        BlenderImporterAPI.dbg.write("\tIterating over Meshes\n")
        for meshObject in context.meshes:
            try:
                BlenderImporterAPI.dbg.write("\t%s\n"%meshObject.name)
                BlenderImporterAPI.dbg.write("\tGetting Material Code\n")
                materialStr = meshObject.data['material'].replace('\x00','')
                BlenderImporterAPI.dbg.write("\tFetching Material from MRL3\n")
                BlenderImporterAPI.dbg.write("\t%s\n"%materialStr)
                filepath = textureFetch(materialStr)
                BlenderImporterAPI.dbg.write("\tFetching File\n")
                textureData = BlenderImporterAPI.fetchTexture(filepath)
                BlenderImporterAPI.dbg.write("\tAssigning Texture to Model\n")
                BlenderImporterAPI.assignTexture(meshObject, textureData)
                BlenderImporterAPI.dbg.write("\tAssigned Texture to Model\n")
            except Exception as e:
                pass
        
    @staticmethod
    def maximizeClipping(context):
        for a in bpy.context.screen.areas:
            if a.type == 'VIEW_3D':
                for s in a.spaces:
                    if s.type == 'VIEW_3D':
                        s.clip_end = 10**9
                        
# =============================================================================
# Helper Methods
# =============================================================================
    @staticmethod
    def parseProperties(properties, assignmentFunction):
        for name, val in sorted(properties.items(), key=lambda x: x[0]):
            assignmentFunction(name,val)
    
    @staticmethod
    def tupleSum(t1,t2):
        return tuple((i+j for i,j in zip(t1,t2)))
    
    @staticmethod
    def normalize(vector):
        factor = sum([v*v for v in vector])
        if not factor:
            return vector
        return tuple([v/factor for v in vector])
        

# =============================================================================
# Mesh Handling
# =============================================================================
    
    @staticmethod
    def createMesh(name, meshpart):
        BlenderImporterAPI.dbg.write("Geometry Construction\n")
        blenderMesh = bpy.data.meshes.new("%s LOD %d"%(name,meshpart["properties"]["lod"]))
        BlenderImporterAPI.dbg.write("Geometry From Pydata\n")
        BlenderImporterAPI.dbg.write("Vertex Count: %d\n"%len(meshpart['vertices']))
        BlenderImporterAPI.dbg.write("Faces %d %d\n"%(min(map(lambda x: min(x,default=0),meshpart["faces"]),default=0), max(map(lambda x: max(x,default=0),meshpart["faces"]),default=0)))
        blenderMesh.from_pydata(meshpart["vertices"],[],meshpart["faces"])
        BlenderImporterAPI.dbg.write("Pydata Loaded\n")
        blenderMesh.update()
        blenderObject = bpy.data.objects.new("%s LOD %d"%(name,meshpart["properties"]["lod"]), blenderMesh)
        BlenderImporterAPI.dbg.write("Geometry Link\n")
        bpy.context.scene.objects.link(blenderObject)
        return blenderMesh, blenderObject
    
    @staticmethod
    def setNormals(normals, meshpart):
        meshpart.update(calc_edges=True)
        #meshpart.normals_split_custom_set_from_vertices(normals)
        
        clnors = array.array('f', [0.0] * (len(meshpart.loops) * 3))
        meshpart.loops.foreach_get("normal", clnors)
        meshpart.polygons.foreach_set("use_smooth", [True] * len(meshpart.polygons))
        
        #meshpart.normals_split_custom_set(tuple(zip(*(iter(clnors),) * 3)))
        meshpart.normals_split_custom_set_from_vertices(normals)
        #meshpart.normals_split_custom_set([normals[loop.vertex_index] for loop in meshpart.loops])
        meshpart.use_auto_smooth = True
        meshpart.show_edge_sharp = True
        
        #db
    
    @staticmethod
    def normalCheck(meshpart):
        normals = {}
        for l in meshpart.loops:
            if l.vertex_index in normals and l.normal != normals[l.vertex_index]:
                raise "Normal Abortion"
            else:
                normals[l.vertex_index]=l.normal
        
    @staticmethod
    def mod3ToBlenderColour(mod3Colour):
        return (mod3Colour.Red/255.0,mod3Colour.Green/255.0,mod3Colour.Blue/255.0,mod3Colour.Alpha/255.0)
    
    @staticmethod
    def setWorldMeshDefault(mesh):
        BlenderImporterAPI.parseProperties({"DefaultMesh-"+prop:mesh[prop] for prop in ModellingAPI.MeshDefaults},bpy.context.scene.__setitem__)
            

# =============================================================================
# Skeleton Methods
# =============================================================================
        
    MTFCormat = Matrix([[0,1,0,0],
                      [-1,0,0,0],
                      [0,0,1,0],            
                      [0,0,0,1]])
    
    @staticmethod
    def createRootNub(miniscene):
        o = bpy.data.objects.new("Bone.%03d"%255, None )
        miniscene["Bone.%03d"%255]=o
        bpy.context.scene.objects.link( o )
        o.show_wire = True
        o.show_x_ray = True
        return
        
    
    @staticmethod
    def createNub(ix, bone, armature, miniscene):
        o = bpy.data.objects.new("Bone.%03d"%ix, None )
        miniscene["Bone.%03d"%ix]=o
        bpy.context.scene.objects.link( o )
        #if bone["parentId"]!=255:
        parentName = "Bone.%03d"%bone["parentId"]
        if parentName not in miniscene:
            BlenderImporterAPI.createNub(bone["parentId"],armature[bone["parentId"]],miniscene)
        o.parent = miniscene[parentName]
        
        o.matrix_local = BlenderImporterAPI.deserializeMatrix("LMatCol",bone)
        o.show_wire = True
        o.show_x_ray = True
        o.show_bounds = True
        BlenderImporterAPI.parseProperties(bone["CustomProperties"],o.__setitem__)
    
    @staticmethod
    def createBone(ix, bone, armature, blenderArmature):
        blenderBone = blenderArmature.edit_bones.new("Bone.%03d"%ix)
        blenderBone.use_inherit_rotation = False
        blenderBone.use_local_location = False
        blenderBone.use_inherit_scale = False
        parent = bone["parentId"]
        if parent != 255:
            parentName = "Bone.%03d"%parent
            if parentName not in blenderArmature.edit_bones:
                BlenderImporterAPI.createBone(parent,armature[parent],armature,blenderArmature)
            parentBone = blenderArmature.edit_bones[parentName]
            blenderBone.parent = parentBone
            head = parentBone.tail
            localMatrix = BlenderImporterAPI.deserializeMatrix("LMatCol",armature[parent])
        else:
            head = Vector((0,0,0))
            localMatrix = Matrix.Identity(4)
        tail = (localMatrix*Vector((head[0],head[1],head[2],1)))[:3]
        if tail == head:
            tail += Vector((0,0,BlenderImporterAPI.MACHINE_EPSILON))
        blenderBone.head = head
        blenderBone.tail = tail
        BlenderImporterAPI.parseProperties(bone["CustomProperties"],blenderBone.__setitem__)
    
    @staticmethod
    def deserializeMatrix(baseString, properties):
        matrix = Matrix(list(map(list,zip(*[properties[baseString+"%d"%column] for column in range(4)]))))
        return matrix
    
    @staticmethod
    def writeWeights(blenderObject, mod3Mesh):
        for groupIx,group in mod3Mesh["weightGroups"].items():
            groupId = "%03d"%groupIx if isinstance(groupIx, int) else str(groupIx) 
            groupName = "Bone.%s"%str(groupId)
            for vertex,weight in group:
                if groupName not in blenderObject.vertex_groups:
                    blenderObject.vertex_groups.new(groupName)#blenderObject Maybe?
                blenderObject.vertex_groups[groupName].add([vertex], weight, 'ADD')
        return
    
    @staticmethod
    def linkChildren(miniscene):
        for ex in range(len(miniscene)-1):
            e = miniscene["Bone.%03d"%ex]
            if e["child"] != 255:
                c = e.constraints.new('CHILD_OF')
                for prop in ["location","rotation","scale"]:
                    for axis in ["x","y","z"]:
                        c.__setattr__("use_%s_%s"%(prop,axis), False)
                c.target=miniscene["Bone.%03d"%e["child"]]
                c.active=False
            del e["child"]
    
# =============================================================================
# UV and Texture Handling
# =============================================================================
             
    @staticmethod
    def fetchTexture(filepath):
        filepath = filepath+".png"
        BlenderImporterAPI.dbg.write("\t%s\n"%filepath)
        if os.path.exists(filepath):
            return bpy.data.images.load(filepath)
        else:
            raise FileNotFoundError("File %s not found"%filepath)
    
    @staticmethod
    def assignTexture(meshObject, textureData):
        for uvLayer in meshObject.data.uv_textures:
            for uv_tex_face in uvLayer.data:
                uv_tex_face.image = textureData
        meshObject.data.update()
        
    @staticmethod
    def createTextureLayer(name, blenderMesh, uv):#texFaces):
        #if bpy.context.active_object.mode!='OBJECT':
        #    bpy.ops.object.mode_set(mode='OBJECT')
        BlenderImporterAPI.dbg.write("\t\tCreating new UV\n")
        blenderMesh.uv_textures.new(name)
        blenderMesh.update()
        BlenderImporterAPI.dbg.write("\t\tCreating BMesh\n")
        blenderBMesh = bmesh.new()
        blenderBMesh.from_mesh(blenderMesh)
        BlenderImporterAPI.dbg.write("\t\tAcquiring UV Layer\n")
        uv_layer = blenderBMesh.loops.layers.uv[name]
        blenderBMesh.faces.ensure_lookup_table()
        BlenderImporterAPI.dbg.write("\t\tBMesh Face Count %d\n"%len(blenderBMesh.faces))
        BlenderImporterAPI.dbg.write("\t\tStarting Looping\n")
        BlenderImporterAPI.dbg.write("\t\tUV Vertices Count %d\n"%len(uv))
        for face in blenderBMesh.faces:
            for loop in face.loops:
                #BlenderImporterAPI.dbg.write("\t%d\n"%loop.vert.index)
                loop[uv_layer].uv = uv[loop.vert.index]
        BlenderImporterAPI.dbg.write("\t\tUVs Edited\n") 
        blenderBMesh.to_mesh(blenderMesh)
        BlenderImporterAPI.dbg.write("\t\tMesh Written Back\n")
        blenderMesh.update()
        BlenderImporterAPI.dbg.write("\t\tMesh Updated\n")
        return blenderMesh.uv_textures[name]
    
    @staticmethod
    def uvFaceCombination(vertexUVMap, FaceList):
        BlenderImporterAPI.dbg.write("\t\tFaces %d %d - UV Count %d\n"%(min(map(min,FaceList)), max(map(max,FaceList)), len(vertexUVMap)))
        #BlenderImporterAPI.dbg.write("UVs %s\n"%str([list(map(lambda x: vertexUVMap[x], face)) for face in FaceList]))
        return sum([list(map(lambda x: vertexUVMap[x], face)) for face in FaceList],[])

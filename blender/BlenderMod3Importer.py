# -*- coding: utf-8 -*-
"""
Created on Sun Mar 31 03:11:30 2019

@author: AsteriskAmpersand
"""

import bpy
import bmesh
import idprop
import array
import os
from mathutils import Vector, Matrix
from collections import OrderedDict
from pathlib import Path
try:
    from ..mod3.ModellingApi import ModellingAPI, debugger
    from ..blender import BlenderSupressor
    from ..blender.BlenderNormals import normalize
    from ..blender.BlenderNodesFunctions import (materialSetup, diffuseSetup, normalSetup,
                                          specularSetup, emissionSetup, finishSetup, rmtSetup, principledSetup)
except:
    import sys
    sys.path.insert(0, r'..\mod3')
    from ModellingApi import ModellingAPI, debugger
    
def processPath(path):
    return os.path.splitext(os.path.basename(path))[0]

class BoneGraph():
    def __init__(self, armature):
        self.bones = {}
        self.boneParentage = {}
        for ix, bone in enumerate(armature):
            bonePoint = BonePoint(ix, bone)
            self.bones[ix] = bonePoint 
            if bone["parentId"] in self.bones:
                self.bones[bone["parentId"]].children.append(bonePoint)
            else:
                if bone["parentId"] not in self.boneParentage:
                    self.boneParentage[bone["parentId"]]=[]
                self.boneParentage[bone["parentId"]].append(bonePoint)
        for parentId in self.boneParentage:
            if parentId != 255:
                self.bones[parentId].children += self.boneParentage[parentId]
        self.roots = self.boneParentage[255]
        
    def root(self):
        return self.roots

class BonePoint():
    def __init__(self, ix, bone):
        self.properties = bone["CustomProperties"]
        self.index = ix
        self.name = "BoneFunction.%03d"%bone["CustomProperties"]["boneFunction"]#%ix
        self.lmatrix = BlenderImporterAPI.deserializeMatrix("LMatCol",bone)
        self.pos = Vector((bone["x"],bone["y"],bone["z"]))
        self.children = []
    def children(self):
        return self.children

class BlenderImporterAPI(ModellingAPI):
    MACHINE_EPSILON = 2**-8
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
    def createEmptyTree(armature, context):
        miniscene = OrderedDict()
        BlenderImporterAPI.createRootNub(miniscene)
        for ix, bone in enumerate(armature):
            if ix not in miniscene:
                BlenderImporterAPI.createNub(ix, bone, armature, miniscene)
        miniscene[255].name = '%s Armature'%processPath(context.path)
        miniscene[255]["Type"] = "MOD3_SkeletonRoot"
        BlenderImporterAPI.linkChildren(miniscene)
        context.armature = miniscene
        return 
    
    @staticmethod
    def createArmature(armature, context):#Skeleton
        filename = processPath(context.path)
        miniscene = OrderedDict()
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
        
        empty = BlenderImporterAPI.createParentBone(blenderArmature)
        boneGraph = BoneGraph(armature)
        for bone in boneGraph.root():
            root = BlenderImporterAPI.createBone(blenderArmature, bone, miniscene)
            root.parent = empty
            #arm.pose.bones[ix].matrix
            
        bpy.ops.object.editmode_toggle()
        BlenderImporterAPI.dbg.write("Loaded Armature\n")
        context.armature = miniscene
        context.skeleton = arm_ob
        return
    
    @staticmethod
    def createMeshParts(meshPartList, omitEmpty, context):
        meshObjects = []
        boundingBoxes = []
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
            BlenderImporterAPI.writeWeights(blenderObject, meshpart, omitEmpty, context)
            #Normals Handling
            BlenderImporterAPI.dbg.write("\tLoading Normals\n")
            BlenderImporterAPI.setNormals(meshpart["normals"],blenderMesh)
            #Colour
            #Needs to enter object mode
            if meshpart["colour"]:
                BlenderImporterAPI.dbg.write("\tLoading Colours\n")
                vcol_layer = blenderMesh.vertex_colors.new()
                for l,col in zip(blenderMesh.loops, vcol_layer.data):
                    try:
                        col.color = BlenderImporterAPI.mod3ToBlenderColour(meshpart["colour"][l.vertex_index])
                    except:
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
            boundingBoxes.append(meshpart["boundingBoxes"])
        context.meshes = meshObjects
        context.boundingBoxes = boundingBoxes
        BlenderImporterAPI.dbg.write("Meshparts Created\n")

    @staticmethod
    def clearSelection():
        for ob in bpy.context.selected_objects:
            ob.select = False
     
    @staticmethod
    def linkEmptyTree(context):
        BlenderImporterAPI.clearSelection()
        armature = context.armature
        for ob in context.meshes:
            for bone in armature:
                modifier = ob.modifiers.new(name = armature[bone].name, type='HOOK')
                modifier.object = armature[bone]
                modifier.vertex_group = armature[bone].name
                modifier.falloff_type = "NONE"
                if not modifier.vertex_group:
                    ob.modifiers.remove(modifier)
                else:
                    bpy.context.scene.objects.active = ob
                    ob.select = True
                    bpy.ops.object.mode_set(mode = 'EDIT')
                    bpy.ops.object.hook_reset(modifier = armature[bone].name)
                    bpy.ops.object.mode_set(mode = 'OBJECT')
                    ob.select = False
                    bpy.context.scene.objects.active = None

    @staticmethod
    def linkArmature(context):
        if hasattr(context,"skeleton"):
            with BlenderSupressor.SupressBlenderOps():
                for mesh in context.meshes:
                    modifier = mesh.modifiers.new(name = "Animation Armature", type='ARMATURE')
                    modifier.object = context.skeleton
                    mesh.parent = context.skeleton
        
    @staticmethod
    def clearScene(context):
        BlenderImporterAPI.dbg.write("Clearing Scene\n")
        for key in list(bpy.context.scene.keys()):
            if type(bpy.context.scene[key]) != idprop.types.IDPropertyGroup:
                del bpy.context.scene[key]
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj)
        #bpy.ops.object.select_all(action='SELECT')
        #bpy.ops.object.delete() 
        for i in bpy.data.images.keys():
            bpy.data.images.remove(bpy.data.images[i])
        BlenderImporterAPI.dbg.write("Scene Cleared\n")
        return

    @staticmethod
    def loadMaterialFromMesh(meshObject, textureFetch):
        try:
            BlenderImporterAPI.dbg.write("\t%s\n"%meshObject.name)
            BlenderImporterAPI.dbg.write("\tGetting Material Code\n")
            materialStr = meshObject.data['material'].replace('\x00','')
            BlenderImporterAPI.dbg.write("\tFetching Material from MRL3\n")
            BlenderImporterAPI.dbg.write("\t%s\n"%materialStr)
            filepath = textureFetch(materialStr)
            BlenderImporterAPI.dbg.write("\tFetching File\n")
            textureData = BlenderImporterAPI.fetchTexture(filepath)
            return textureData
        except Exception as e:
            BlenderImporterAPI.dbg.write(str(e))
            raise

    @staticmethod
    def importTextures(textureFetch, context):
        BlenderImporterAPI.dbg.write("Importing Texture\n")
        if not textureFetch:
            BlenderImporterAPI.dbg.write("Failed to Import Texture\n")
            return
        BlenderImporterAPI.dbg.write("\tIterating over Meshes\n")
        for meshObject in context.meshes:
            try:
                textureData = BlenderImporterAPI.loadMaterialFromMesh(meshObject,textureFetch)
                BlenderImporterAPI.dbg.write("\tAssigning Texture to Model\n")
                BlenderImporterAPI.assignTexture(meshObject, textureData)
                BlenderImporterAPI.dbg.write("\tAssigned Texture to Model\n")
            except:
                pass

    @staticmethod
    def setupMap(typing,setupFunction,qualifiedFetch,meshObject):
        fetch = qualifiedFetch(typing)
        tex = BlenderImporterAPI.loadMaterialFromMesh(meshObject,fetch)
        BlenderImporterAPI.dbg.write("\t\t\tTexture Fetched\n")
        nodeEnd = setupFunction(tex)
        BlenderImporterAPI.dbg.write("\t\t\tAssigned %s to Node Tree\n"%typing)
        return nodeEnd

    @staticmethod
    def meshImportMaterials(filename,meshObject,textureFetch):
        mo=meshObject
        BlenderImporterAPI.dbg.write("\t\tImporting Material to Mesh\n")
        qf = lambda y: lambda x: textureFetch(x,y)
        nodeTree = materialSetup(filename,mo)
        if nodeTree is None:
            return
        preapplyTree = lambda x: lambda y: x(nodeTree,y)
        mainNode = principledSetup(nodeTree)
        next(mainNode)
        for mapName,mapFunc in zip(["Albedo","Normal","FxMap","RMT","Emissive"],
                                   [diffuseSetup,normalSetup,specularSetup,rmtSetup,emissionSetup]):
            try:
                currentNode = BlenderImporterAPI.setupMap(mapName,preapplyTree(mapFunc),qf,mo)
                mainNode.send(currentNode)
            except Exception as e:
                BlenderImporterAPI.dbg.write(str(e)+'\n')
                mainNode.send("")
        try:
            finishSetup(nodeTree,next(mainNode))
            return
        except Exception as e:
            BlenderImporterAPI.dbg.write(str(e)+'\n')
            return

    @staticmethod
    def importMaterials(textureFetch, context):
        BlenderImporterAPI.dbg.write("Importing Materials\n")
        if not textureFetch:
            BlenderImporterAPI.dbg.write("Failed to Import Materials\n")
            return
        BlenderImporterAPI.dbg.write("\tIterating over Meshes\n")
        for meshObject in context.meshes:
            BlenderImporterAPI.meshImportMaterials(Path(context.path).stem,meshObject,textureFetch)
            
                  
        
    @staticmethod       
    def overrideMeshDefaults(context):
        if context.meshes:
            BlenderImporterAPI.setWorldMeshDefault((context.meshes[0].data))
        
    @staticmethod
    def maximizeClipping(context):
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        if meshes:
            minBox = Vector(map(min,zip(*[mesh.bound_box[0] for mesh in meshes])))
            maxBox = Vector(map(max,zip(*[mesh.bound_box[6] for mesh in meshes])))
        else:
            minBox = Vector([0,0,0])
            maxBox = Vector([0,0,0])
        span = max(max(maxBox-minBox)*2,10**3)
        for a in bpy.context.screen.areas:
            if a.type == 'VIEW_3D':
                for s in a.spaces:
                    if s.type == 'VIEW_3D':
                        s.clip_end = span
                        
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
            return Vector(vector)
        return Vector([v/factor for v in vector])
        

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
        meshpart.normals_split_custom_set_from_vertices([normalize(v) for v in normals])
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
        o = bpy.data.objects.new("Root", None )
        miniscene[255]=o
        bpy.context.scene.objects.link( o )
        o.show_wire = True
        o.show_x_ray = True
        return
        
    
    @staticmethod
    def createNub(ix, bone, armature, miniscene):
        #raise ValueError(bone.keys())
        #o = bpy.data.objects.new("Bone.%03d"%ix, None )
        #if preserveOrdering:
        #    name = "Bone.%03d" % ix
        #else:
        name = "BoneFunction.%03d" % bone["CustomProperties"]["boneFunction"]
        o = bpy.data.objects.new(name, None )#ix
        miniscene[ix]=o
        bpy.context.scene.objects.link( o )
        #if bone["parentId"]!=255:
        parentName = bone["parentId"]
        if parentName not in miniscene:
            BlenderImporterAPI.createNub(bone["parentId"],armature[bone["parentId"]],miniscene)
        o.parent = miniscene[parentName]
        
        o.matrix_local = BlenderImporterAPI.deserializeMatrix("LMatCol",bone)
        o.show_wire = True
        o.show_x_ray = True
        o.show_bounds = True
        BlenderImporterAPI.parseProperties(bone["CustomProperties"],o.__setitem__)
        o["indexHint"] = ix# if preserveOrdering else -1
    
    class DummyBone():
        def __init__(self):
            self.matrix = Matrix.Identity(4)
            self.head = Vector([0,-1,0])
            self.tail = Vector([0,0,0])
            self.magnitude = 1
            
    @staticmethod
    def createParentBone(armature):
        bone = armature.edit_bones.new("Root")
        bone["boneFunction"] = -1
        bone.head = Vector([0, 0, 0])
        bone.tail = Vector([0, BlenderImporterAPI.MACHINE_EPSILON, 0])
        bone.matrix = Matrix.Identity(4)        
        return bone
        
    @staticmethod
    def createBone(armature, obj, miniscene, parent_bone = None):
        bone = armature.edit_bones.new(obj.name)
        miniscene[obj.index] = obj
        bone.head = Vector([0, 0, 0])
        bone.tail = Vector([0, BlenderImporterAPI.MACHINE_EPSILON, 0])#Vector([0, 1, 0])
        #for prop in obj.keys():
        #    bone[prop] = obj[prop]
        if not parent_bone:
            parent_bone = BlenderImporterAPI.DummyBone()#matrix = Identity(4), #boneTail = 0,0,0, boneHead = 0,1,0
        bone.matrix = parent_bone.matrix * obj.lmatrix
        for child in obj.children:
            nbone = BlenderImporterAPI.createBone(armature, child, miniscene, bone)
            nbone.parent = bone
        BlenderImporterAPI.parseProperties(obj.properties,bone.__setitem__)
        return bone
    
    @staticmethod
    def deserializeMatrix(baseString, properties):
        matrix = Matrix(list(map(list,zip(*[properties[baseString+"%d"%column] for column in range(4)]))))
        return matrix
    
    @staticmethod
    def writeWeights(blenderObject, mod3Mesh, omitEmpty, context):
        armature = context.armature
        boundGroups = set((box.bone() for box in mod3Mesh["boundingBoxes"]))
        BlenderImporterAPI.dbg.write("\t\t\tGroups: %s\n"%(list(boundGroups)))
        for groupIx,group in mod3Mesh["weightGroups"].items():                       
            groupIndex = groupIx if isinstance(groupIx, int) else groupIx[0] 
            #BlenderImporterAPI.dbg.write("\t\t\t%s\n"%(str(groupIndex)))
            #groupIndex is assured to be an int, which allows us to check against the bounding box values
            if groupIndex not in boundGroups:
                BlenderImporterAPI.dbg.write("\t\t\tGroup not in Bounding Boxes: %s\n"%(str(groupIndex)))
            if groupIndex in boundGroups or not omitEmpty:
                if armature and groupIndex in armature:
                    targetName = armature[groupIndex].name
                    tindex = int(targetName.split(".")[1])
                    groupId = "%03d"%tindex if isinstance(groupIx, int) else "(%03d,%s)"%(tindex,groupIx[1])
                else:
                    groupId = str(groupIx)
                groupName = "BoneFunction.%s"%groupId
                for vertex,weight in group:
                    if groupName not in blenderObject.vertex_groups:
                        blenderObject.vertex_groups.new(groupName)#blenderObject Maybe?
                    blenderObject.vertex_groups[groupName].add([vertex], weight, 'ADD')
        return
    
    @staticmethod
    def linkChildren(miniscene):
        for ex in range(len(miniscene)-1):
            e = miniscene[ex]
            if e["child"] != 255:
                e.MHW_Symmetric_Pair = miniscene[e["child"]]
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

# =============================================================================
# Bounding Box Handling
# =============================================================================
    @staticmethod
    def loadAABB(box,name,armature):
        name = "%s_AABB_Bounding_Box"%name
        lattice = bpy.data.lattices.new(name)
        lattice_ob = bpy.data.objects.new(name, lattice)
        lattice_ob.scale = box.scale()
        lattice_ob.location = lattice_ob.location + box.center()
        constraint = lattice_ob.constraints.new("CHILD_OF")
        constraint.target = armature[box.bone()] if box.bone() in armature else None
        lattice["Type"] = "MOD3_BoundingBox_AABB"
        bpy.context.scene.objects.link(lattice_ob)
        bpy.context.scene.update()
        return lattice_ob
    
    @staticmethod
    def loadMVBB(box,name,armature):
        name = "%s_MVBB_Bounding_Box"%name
        lattice = bpy.data.lattices.new(name)
        lattice_ob = bpy.data.objects.new(name, lattice)
        #for prop,value in box.metadata().items():
        #    lattice[prop] = value
        lattice_ob.matrix_world = box.matrix()
        lattice_ob.scale = box.vector()*2
        
        constraint = lattice_ob.constraints.new("CHILD_OF")
        if box.bone() not in armature:
            lattice_ob["bone_index"] = box.bone()
        constraint.target = armature[box.bone()] if box.bone() in armature else None
        lattice["Type"] = "MOD3_BoundingBox_MVBB"
        bpy.context.scene.objects.link(lattice_ob)
        bpy.context.scene.update()
        return lattice_ob

    @staticmethod
    def loadBoundingBoxes(boundingBoxes, context):
        #elementWiseMult = lambda vec1, vec2: Vector(x * y for x, y in zip(vec1, vec2))
        for bbMesh, boxes in zip(context.meshes, context.boundingBoxes):
            for box in boxes:
                name = Path(context.path).stem
                armature = context.armature
                aabb = BlenderImporterAPI.loadAABB(box,name,armature)
                mvbb =BlenderImporterAPI.loadMVBB(box,name,armature)
                aabb.parent = bbMesh
                mvbb.parent = bbMesh
                #aabb.MHW_Symmetric_Pair = bbMesh
                #mvbb.MHW_Symmetric_Pair = bbMesh
            
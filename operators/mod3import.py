# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:09:29 2019

@author: AsteriskAmpersand
"""
import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

from ..mod3 import Mod3ImporterLayer as Mod3IL
from ..blender import BlenderMod3Importer as Api
from ..blender import BlenderSupressor
from ..common import FileLike as FL


class Context():
    def __init__(self, path, meshes, armature):
        self.path = path
        self.meshes = meshes
        self.armature = armature
        self.setDefaults = False

class ImportMOD3(Operator, ImportHelper):
    bl_idname = "custom_import.import_mhw_mod3"
    bl_label = "Load MHW MOD3 file (.mod3)"
    bl_options = {'REGISTER', 'PRESET', 'UNDO'}
 
    # ImportHelper mixin class uses this
    filename_ext = ".mod3"
    filter_glob = StringProperty(default="*.mod3", options={'HIDDEN'}, maxlen=255)

    clear_scene = BoolProperty(
        name = "Clear scene before import.",
        description = "Clears all contents before importing",
        default = True)
    maximize_clipping = BoolProperty(
        name = "Maximizes clipping distance.",
        description = "Maximizes clipping distance to be able to see all of the model at once.",
        default = True)
    high_lod = BoolProperty(
        name = "Only import high LOD parts.",
        description = "Skip meshparts with low level of detail.",
        default = True)
    import_header = BoolProperty(
        name = "Import File Header.",
        description = "Imports file headers as scene properties.",
        default = True)
    import_meshparts = BoolProperty(
        name = "Import Meshparts.",
        description = "Imports mesh parts as meshes.",
        default = True)
    import_textures = BoolProperty(
        name = "Import Textures.",
        description = "Imports texture as specified by mrl3.",
        default = True)
    import_materials = BoolProperty(
        name = "Import Materials.",
        description = "Imports maps as materials as specified by mrl3.",
        default = False)
    load_group_functions = BoolProperty(
        name = "Load Bounding Boxes.",
        description = "Loads the mod3 as bounding boxes.",
        default = False,
        )
    texture_path = StringProperty(
        name = "Texture Source",
        description = "Root directory for the MRL3 (Native PC if importing from a chunk).",
        default = "")
    import_skeleton = EnumProperty(
        name = "Import Skeleton.",
        description = "Imports the skeleton as an armature.",
        items = [("None","Don't Import","Does not import the skeleton.",0),
                  ("EmptyTree","Empty Tree","Import the skeleton as a tree of empties",1),
                  ("Armature","Animation Armature","Import the skeleton as a blender armature",2),
                  ],
        default = "EmptyTree") 
    weight_format = EnumProperty(
        name = "Weight Format",
        description = "Preserves capcom scheme of having repeated weights and negative weights by having multiple weight groups for each bone.",
        items = [("Group","Standard","Weights under the same bone are grouped",0),
                  ("Split","Split Weight Notation","Mirrors the Mod3 separation of the same weight",1),
                  ("Slash","Split-Slash Notation","As split weight but also conserves weight order",2),
                  ],
        default = "Group")

    def execute(self,context):
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        bpy.ops.object.select_all(action='DESELECT')
        Mod3File = FL.FileLike(open(self.properties.filepath,'rb').read())
        BApi = Api.BlenderImporterAPI()
        options = self.parseOptions()
        blenderContext = Context(self.properties.filepath,{},None)
        with BlenderSupressor.SupressBlenderOps():
            Mod3IL.Mod3ToModel(Mod3File, BApi, options).execute(blenderContext)   
            bpy.ops.object.select_all(action='DESELECT')
        #bpy.ops.object.mode_set(mode='OBJECT')
        #bpy.context.area.type = 'INFO'
        return {'FINISHED'}
    
    def parseOptions(self):
        options = {}
        if self.clear_scene:
            options["Clear"]=True
        if self.maximize_clipping:
            options["Max Clip"]=True
        if self.high_lod:
            options["High LOD"]=True
        if self.import_header:
            options["Scene Header"]=True
        if self.import_skeleton != "None":
            options["Skeleton"]=self.import_skeleton
        if self.import_meshparts:
            options["Mesh Parts"]=True
        if self.high_lod:
            options["Only Highest LOD"]=True
        if self.import_textures:
            options["Import Textures"]=self.texture_path
        if self.import_materials:
            options["Import Materials"]=self.texture_path
        if self.load_group_functions:
            options["Load Groups and Functions"]=True
        options["Split Weights"]=self.weight_format
        return options
    
def menu_func_import(self, context):
    self.layout.operator(ImportMOD3.bl_idname, text="MHW MOD3 (.mod3)")

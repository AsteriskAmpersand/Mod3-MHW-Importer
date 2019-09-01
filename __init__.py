# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 13:38:47 2019

@author: AsteriskAmpersand
"""
#from .dbg import dbg_init
#dbg_init()

content=bytes("","UTF-8")
bl_info = {
    "name": "MHW Mod3 Model Importer",
    "category": "Import-Export",
    "author": "AsteriskAmpersand (Code) & CrazyT (Structure)",
    "location": "File > Import-Export",
    "version": (2,0,0),
    "blender": (2, 80, 0)
}
 
import bpy

from .operators.mod3import import ImportMOD3
from .operators.mod3export import ExportMOD3
from .operators.mod3import import menu_func_import
from .operators.mod3export import menu_func_export

classes = (
    ImportMOD3,
    ExportMOD3,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

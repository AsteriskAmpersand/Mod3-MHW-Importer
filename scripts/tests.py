# -*- coding: utf-8 -*-
"""
Created on Sun Mar 31 03:56:23 2019

@author: AsteriskAmpersand
"""

from pathlib import Path
from random import randint
import bpy
import filecmp



base = Path(r"G:\Mod3ExporterTests")
blocktypes = set()
chunkPath = r"E:\MHW\Merged"
nativePC = Path(r"E:\Program Files (x86)\Steam\steamapps\common\Monster Hunter World\nativePC")
filelist = list(Path(chunkPath).rglob("*.mod3"))

randomChoices = []
for i in range(50):
    r=randint(0,len(filelist)-1)
    while r in randomChoices: r=randint(0,len(filelist)-1)
    randomChoices.append(r)

options = {"high_lod" : False,
    "import_textures" : False,
    "preserve_weight" : True}

errors = []
for r in randomChoices:
    file = filelist[r]
    try: bpy.ops.custom_import.import_mhw_mod3(filepath=str(file),**options)
    except:
        errors.append("Problem importing %s"%file)
        continue
    model1 = str(base.joinpath(file.name))
    try: bpy.ops.custom_export.export_mhw_mod3(filepath=model1)
    except:
        errors.append("Problem exporting %s"%file)
        continue    
    try: bpy.ops.custom_import.import_mhw_mod3(filepath=model1,**options)
    except:
        errors.append("Problem re-importing %s"%file.name)
        continue  
    model2 = str(base.joinpath("Modded-"+file.name))
    try: bpy.ops.custom_export.export_mhw_mod3(filepath=model2)
    except:
        errors.append("Problem re-exporting %s"%file.name)
        continue          
    if not filecmp.cmp(model1, model2):
        errors.append("Changes on %s when cycling."%(file.name))
        
for e in errors: 
    print(e)

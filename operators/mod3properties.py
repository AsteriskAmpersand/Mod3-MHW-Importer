# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 22:11:15 2020

@author: AsteriskAmpersand
"""
import bpy

def bone_poll(self,object):
    return object.get('boneFunction')

symmetricPair = bpy.props.PointerProperty(type=bpy.types.Object,poll=bone_poll)

def bone_poll(self,object):
    return object.get('enabled')

class MHWSkeletonPanel(bpy.types.Panel):
    bl_idname = "MHW_PT_skeleton"
    bl_label = "MHW Skeleton"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return (context.object is not None and context.object.type == "EMPTY")

    def draw(self, context):
        layout = self.layout

        obj = context.object.MHWSkeleton
        row = layout.column()
        if not obj.enabled:
            row.prop(obj,"enabled")
        else:
            row.prop(obj,"enabled")
            row.prop(obj, "symmetricPair")
            row.prop(obj, "boneFunction")
            row.prop(obj, "indexHint")
            row.prop(obj, "unkn2")

#, type=bpy.types.Object, poll=poll_mhr_bone
class MHWSkeleton(bpy.types.PropertyGroup):
    symmetricPair = bpy.props.PointerProperty(name = "Symmetric Pair")
    boneFunction = bpy.props.PointerProperty(name = "Bone Function",default = -1)
    indexHint = bpy.props.PointerProperty(name = "Sort Priority",default = -1)
    unkn2 = bpy.props.FloatProperty(name = "Envelope",default = 0)
    enabled = bpy.props.FloatProperty(name = "MHW Enabled",default = False)
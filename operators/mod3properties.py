# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 22:11:15 2020

@author: AsteriskAmpersand
"""
import bpy

def bone_poll(self,object):
    return object.get('boneFunction')

symmetricPair = bpy.props.PointerProperty(type=bpy.types.Object,poll=bone_poll)

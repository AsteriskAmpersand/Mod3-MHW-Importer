# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 00:15:34 2019

@author: AsteriskAmpersand
"""
import bpy



#setup scheme from https://i.stack.imgur.com/cdRIK.png
def createTexNode(nodeTree,color,texture,name):
    baseType = "ShaderNodeTexImage"
    node = nodeTree.nodes.new(type=baseType)
    node.color_space = color
    node.image = texture
    node.name = name
    return node

def materialSetup(blenderObj,*args):
    bpy.data.scenes["Scene"].render.engine = 'CYCLES'
    mat = bpy.data.materials.new(name="RenderMaterial")
    blenderObj.data.materials.append(mat)
    mat.use_nodes=True
    nodes = mat.node_tree.nodes
    for node in nodes:
        nodes.remove(node)
    return mat.node_tree

def principledSetup(nodeTree):
    bsdfNode = nodeTree.nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdfNode.name = "Principled BSDF"
    endNode = bsdfNode
    diffuseNode = yield
    if diffuseNode:
        transparentNode = nodeTree.nodes.new(type="ShaderNodeBsdfTransparent")
        alphaMixerNode = nodeTree.nodes.new(type="ShaderNodeMixShader")
        nodeTree.links.new(diffuseNode.outputs[0],bsdfNode.inputs[0])
        nodeTree.links.new(diffuseNode.outputs[1],alphaMixerNode.inputs[0])
        nodeTree.links.new(transparentNode.outputs[0],alphaMixerNode.inputs[1])
        nodeTree.links.new(endNode.outputs[0],alphaMixerNode.inputs[2])
        endNode = alphaMixerNode
    normalNode = yield
    if normalNode:
        nodeTree.links.new(normalNode.outputs[0],bsdfNode.inputs["Normal"])
    specularNode = yield
    if specularNode:
        nodeTree.links.new(specularNode.outputs[0],bsdfNode.inputs[5])
    pair = yield
    if pair:
        roughness,metalicness = pair
        nodeTree.links.new(roughness.outputs[0],bsdfNode.inputs[7])
        nodeTree.links.new(metalicness.outputs[1],bsdfNode.inputs[4])
    emissiveNode = yield
    if emissiveNode:
        addNode = nodeTree.nodes.new(type="ShaderNodeAddShader")
        nodeTree.links.new(endNode.outputs[0],addNode.inputs[0])
        nodeTree.links.new(emissiveNode.outputs[0],addNode.inputs[1])
        #Create Add Node for emissive and mix shader with emissive
        endNode = addNode
    yield
    yield endNode

def diffuseSetup(nodeTree,texture,*args):
    #Create DiffuseTexture
    diffuseNode = createTexNode(nodeTree,"COLOR",texture,"Diffuse Texture")
    #Create DiffuseBSDF
    #bsdfNode = nodeTree.nodes.new(type="ShaderNodeBsdfDiffuse")
    #bsdfNode.name = "Diffuse BSDF"          
    #Plug Diffuse Texture to BDSF (color -> color)
    #nodeTree.links.new(diffuseNode.outputs[0],bsdfNode.inputs[0])
    return diffuseNode

def normalSetup(nodeTree,texture,*args):
    #Create NormalMapData
    normalNode = createTexNode(nodeTree,"NONE",texture,"Normal Texture")
    #Create InvertNode
    inverterNode = nodeTree.nodes.new(type="ShaderNodeInvert")
    inverterNode.name = "Normal Inverter"
    #Create NormalMapNode
    normalmapNode = nodeTree.nodes.new(type="ShaderNodeNormalMap")
    normalmapNode.name = "Normal Map"
    #Plug Normal Data to Node (color -> color)
    nodeTree.links.new(normalNode.outputs[0],inverterNode.inputs[1])
    nodeTree.links.new(inverterNode.outputs[0],normalmapNode.inputs[1])
    return normalmapNode
    
def specularSetup(nodeTree,texture,*args):
    #Create SpecularityMaterial
    specularNode = createTexNode(nodeTree,"NONE",texture,"Specular Texture")
    #Create RGB Curves
    curveNode = nodeTree.nodes.new(type="ShaderNodeRGBCurve")
    curveNode.name = "Specular Curve"
    #Plug Specularity Color to RGB Curves (color -> color)
    nodeTree.links.new(specularNode.outputs[0],curveNode.inputs[0])
    return curveNode
    
def emissionSetup(nodeTree,texture,*args):
    return "" #Commented out, it's not really possible to work withit without the parameters
    #Create EmissionMap
    emissionNode = createTexNode(nodeTree,"NONE",texture,"Emission Texture")
    #Create Emission
    emissionMap = nodeTree.nodes.new(type="ShaderNodeEmission")
    emissionMap.name = "Emission Map"
    #Create Separate HSV
    brightnessMap = nodeTree.nodes.new(type="ShaderNodeSeparateHSV")
    brightnessMap.name = "Emission Brightness"
    #Plug the base emission to the node
    nodeTree.links.new(emissionNode.outputs[0],emissionMap.inputs[0])
    #Get Valuation as a Strength Map
    nodeTree.links.new(emissionNode.outputs[0],brightnessMap.inputs[0])
    nodeTree.links.new(brightnessMap.outputs[2],emissionMap.inputs[1])
    return emissionMap

#setup scheme from https://i.stack.imgur.com/TdK1W.png + https://i.stack.imgur.com/40vbG.jpg
def rmtSetup(nodeTree,texture,*args):
    #TODO - Complete Nodes
    #Create RMTMap
    rmtNode = createTexNode(nodeTree,"COLOR",texture,"RMT Texture")
    #Create Separate RGB
    splitterNode = nodeTree.nodes.new(type="ShaderNodeSeparateRGB")
    splitterNode.name = "RMT Splitter"
    #Create Metallicness
    #Create Roughness - Create InvertNode
    inverterNode = nodeTree.nodes.new(type="ShaderNodeInvert")
    inverterNode.name = "Roughness Inverter"
    #Tex To Splitter
    nodeTree.links.new(rmtNode.outputs[0],splitterNode.inputs[0])
    #Splitter to Inverter
    nodeTree.links.new(splitterNode.outputs[0],inverterNode.inputs[0])
    return inverterNode,splitterNode#
    
def finishSetup(nodeTree, endNode):
    outputNode = nodeTree.nodes.new(type="ShaderNodeOutputMaterial")
    nodeTree.links.new(endNode.outputs[0],outputNode.inputs[0])
    return
# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 00:15:34 2019

@author: AsteriskAmpersand
"""
import bpy

def setLocation(node,location):
    x,y = location
    node.location = (x-14)*100,-y*100

#setup scheme from https://i.stack.imgur.com/cdRIK.png
def createTexNode(nodeTree,color,texture,name):
    baseType = "ShaderNodeTexImage"
    node = nodeTree.nodes.new(type=baseType)
    node.color_space = color
    node.image = texture
    node.name = name
    return node

def materialSetup(blenderObj,*args):
    matName = blenderObj.data["material"].replace("\x00","") if "material" in blenderObj.data else "RenderMaterial"
    bpy.context.scene.render.engine = 'CYCLES'
    if matName in bpy.data.materials:
        blenderObj.data.materials.append(bpy.data.materials[matName])
        return None
    mat = bpy.data.materials.new(name=matName)
    blenderObj.data.materials.append(mat)
    mat.use_nodes=True
    nodes = mat.node_tree.nodes
    for node in nodes:
        nodes.remove(node)
    return mat.node_tree

def principledSetup(nodeTree):
    bsdfNode = nodeTree.nodes.new(type="ShaderNodeBsdfPrincipled")
    setLocation(bsdfNode,(6,0))
    bsdfNode.name = "Principled BSDF"
    endNode = bsdfNode
    diffuseNode = yield
    if diffuseNode:
        transparentNode = nodeTree.nodes.new(type="ShaderNodeBsdfTransparent")
        setLocation(transparentNode,(6,7))
        alphaMixerNode = nodeTree.nodes.new(type="ShaderNodeMixShader")
        setLocation(alphaMixerNode,(10,1))
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
    rmtTern = yield
    if rmtTern:
        roughness,splitter,subsurface = rmtTern
        nodeTree.links.new(roughness.outputs[0],bsdfNode.inputs[7])
        nodeTree.links.new(splitter.outputs[1],bsdfNode.inputs[4])
        translucencyNode = nodeTree.nodes.new(type="ShaderNodeBsdfTranslucent")
        setLocation(translucencyNode,(10,3))
        translucentMixerNode = nodeTree.nodes.new(type="ShaderNodeMixShader")
        setLocation(translucentMixerNode,(12,0))
        
        if diffuseNode:nodeTree.links.new(diffuseNode.outputs[0],translucencyNode.inputs[0])#color
        if normalNode: nodeTree.links.new(normalNode.outputs[0],translucencyNode.inputs[1])#normal
        
        nodeTree.links.new(splitter.outputs[2],translucentMixerNode.inputs[0])
        nodeTree.links.new(translucencyNode.outputs[0],translucentMixerNode.inputs[1])
        
        nodeTree.links.new(endNode.outputs[0],translucentMixerNode.inputs[2])
        nodeTree.links.new(subsurface.outputs[1],bsdfNode.inputs[1])
        if diffuseNode: nodeTree.links.new(diffuseNode.outputs[1],bsdfNode.inputs[3])
        endNode = translucentMixerNode
        
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
    setLocation(diffuseNode,(0,0))
    #Create DiffuseBSDF
    #bsdfNode = nodeTree.nodes.new(type="ShaderNodeBsdfDiffuse")
    #bsdfNode.name = "Diffuse BSDF"          
    #Plug Diffuse Texture to BDSF (color -> color)
    #nodeTree.links.new(diffuseNode.outputs[0],bsdfNode.inputs[0])
    return diffuseNode

def normalSetup(nodeTree,texture,*args):
    #Create NormalMapData
    normalNode = createTexNode(nodeTree,"NONE",texture,"Normal Texture")
    setLocation(normalNode,(0,6))
    #Create InvertNode
    inverterNode = nodeTree.nodes.new(type="ShaderNodeInvert")
    inverterNode.name = "Normal Inverter"
    setLocation(inverterNode,(2,6))
    #Create NormalMapNode
    normalmapNode = nodeTree.nodes.new(type="ShaderNodeNormalMap")
    normalmapNode.name = "Normal Map"
    setLocation(normalmapNode,(4,6))
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
    #Create RMTMap
    rmtNode = createTexNode(nodeTree,"COLOR",texture,"RMT Texture")
    setLocation(rmtNode,(0,3))
    #Create Separate RGB
    splitterNode = nodeTree.nodes.new(type="ShaderNodeSeparateRGB")
    splitterNode.name = "RMT Splitter"
    setLocation(splitterNode,(2,1))
    #Create Metallicness
    #Create Roughness - Create InvertNode
    inverterNode = nodeTree.nodes.new(type="ShaderNodeInvert")
    inverterNode.name = "Roughness Inverter"
    setLocation(inverterNode,(4,2))
    #Tex To Splitter
    nodeTree.links.new(rmtNode.outputs[0],splitterNode.inputs[0])
    #Splitter to Inverter
    nodeTree.links.new(splitterNode.outputs[0],inverterNode.inputs[0])
    return inverterNode,splitterNode,rmtNode

def furSetup(nodeTree,texture,*args):
    #TODO - Actually Finish This 
    #Create FMMap
    fmNode = createTexNode(nodeTree,"COLOR",texture,"FM Texture")
    #Separate RGB
    splitterNode = nodeTree.nodes.new(type="ShaderNodeSeparateRGB")
    splitterNode.name = "FM Splitter"
    nodeTree.links.new(fmNode.outputs[0],splitterNode.inputs[0])
    #Create Input
    inputNode = nodeTree.nodes.new(type="NodeReroute")
    inputNode.name = "Reroute Node"
    #Create Roughness - Create InvertNode
    inverterNode = nodeTree.nodes.new(type="ShaderNodeInvert")
    inverterNode.name = "Fur Inverter"
    nodeTree.links.new(splitterNode.outputs[1],inverterNode.inputs[1])
    #Create HairBSDF
    transmissionNode = nodeTree.nodes.new(type="ShaderNodeHairBSDF")
    transmissionNode.component = "TRANSMISSION"
    reflectionNode = nodeTree.nodes.new(type="ShaderNodeHairBSDF")
    reflectionNode.component = "REFLECTION"
    for targetNode in [transmissionNode,reflectionNode]:
        nodeTree.links.new(inputNode.outputs[0],targetNode.inputs[0])
        nodeTree.links.new(splitterNode.outputs[0],targetNode.inputs[1])
        nodeTree.links.new(splitterNode.outputs[1],targetNode.inputs[2])
        nodeTree.links.new(inverterNode.outputs[0],targetNode.inputs[3])
    hairNode = nodeTree.nodes.new(type="ShaderNodeMixShader")
    nodeTree.links.new(transmissionNode.outputs[0],hairNode.inputs[1])
    nodeTree.links.new(reflectionNode.outputs[0],hairNode.inputs[2])
    return 
    
    
    
def finishSetup(nodeTree, endNode):
    outputNode = nodeTree.nodes.new(type="ShaderNodeOutputMaterial")
    nodeTree.links.new(endNode.outputs[0],outputNode.inputs[0])
    return
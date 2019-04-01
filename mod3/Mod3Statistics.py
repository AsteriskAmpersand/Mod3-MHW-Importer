# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 23:16:15 2019

@author: AsteriskAmpersand
"""

import Mod3
from FileLike import FileLike
from pathlib import Path
import sys
sys.path.insert(0, r'..\common')
sys.path.insert(0, r'..\mod3')
sys.path.insert(0, r'..\mrl3')
from Matrices import Matrix
from Mod3VertexBuffers import Mod3Vertex

class progbar():
    def __init__(self, count, length):
        self.count = count
        self.current = 0
        self.length = length
        self.upper()
    def upper(self):
        print("_"*self.length)
    def tic(self):
        if int((self.current+1)*self.length/self.count)-int(self.current*self.length/self.count)!=0:
            print("█", end='')
        self.current += 1
    def pickback(self):
        self.upper()
        print("█"*int((self.current+1)*self.length/self.count), end='')

def getAbsoluteMatrix(Skeleton, Matriz, boneIx):
    parentId = Skeleton[boneIx].parentId
    if parentId == 255:
        parentMatrix = Matrix((4,4),identity=True)
    else:
        parentMatrix = Matriz[parentId][1]
    return Matriz[boneIx][0].invert()*parentMatrix
    
    """
    if boneIx in World:
        return World[boneIx]
    parentId = Skeleton[boneIx].parentId
    if parentId == 255:
        World[boneIx]=Matriz[boneIx][0]
        return Matrix((4,4),identity = True)
    else:
        World[boneIx] = getAbsoluteMatrix(Skeleton, Matriz, World, parentId)*Matriz[boneIx][0]
        return World[boneIx]
    """     
            
    

#import sys
#output = open(r'G:\Wisdom\BitInsanity.txt', 'w')
#sys.stdout = output
#with  as sys.stdout:

base = r"G:\Mod3ExporterTests"
blocktypes = set()
chunkPath = r"E:\MHW\Merged"
nativePC = Path(r"E:\Program Files (x86)\Steam\steamapps\common\Monster Hunter World\nativePC")
filelist = list(Path(chunkPath).rglob("*.mod3"))

pbar = progbar(len(filelist),50)
blocktypeListing = {Mod3Vertex.blocklist[key]["name"]:set() for key in Mod3Vertex.blocklist}
for file in filelist:
    fileHandle = open(file,'rb')   
    binaryData = fileHandle.read()
    fileHandle.close()
    pseudofile = FileLike(binaryData)
    model = Mod3.Mod3()
    model.marshall(pseudofile)
    for ix, mesh in enumerate(model.MeshParts):
        blocktypeListing[Mod3Vertex.blocklist[mesh.Header.blocktype]["name"]].add(file)

    pbar.tic()
btype = open(r"G:\Wisdom\blocktypes.txt","w")
separator = "============================================"
for key in sorted(blocktypeListing.keys()):
    btype.write("\n\n%s%s%s\n"%(separator,key,separator))
    for entry in blocktypeListing[key]:
        btype.write("%s\n"%entry)
btype.close()
print("Done")


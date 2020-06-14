# -*- coding: utf-8 -*-
"""
Created on Sun Jun  7 23:17:22 2020

@author: AsteriskAmpersand
"""
try:
    from ..boundingbox.mvbb import calculateMVBB
    from ..boundingbox.msbr import calculateMSBR
    from ..boundingbox.mvbbApprox import (recursiveScan,
                                            diameterHeuristic,
                                            minPrincipal,
                                            maxPrincipal,
                                            allPrincipals,
                                            barequetHar)
    from ..boundingbox.chull import ConvexHull
except:
    import sys
    sys.path.insert(0, r'..\boundingbox')
    from mvbb import calculateMVBB
    from msbr import calculateMSBR
    from chull import ConvexHull
    from mvbbApprox import (recursiveScan,
                            diameterHeuristic,
                            minPrincipal,
                            maxPrincipal,
                            allPrincipals,
                            barequetHar)

def estimateBoundingBox(points):
    hV,hE = ConvexHull(points)
    return allPrincipals(hV,hE)

#Try 3d Convex Hull if Coplanar check if Colinear

if __name__ in "__main__":
    from mathutils import Vector
    import time
    import random
    from pathlib import Path
    sys.path.insert(0, r'..\common')
    sys.path.insert(0, r'..\mod3')
    import FileLike as FL
    from Mod3 import Mod3
    import numpy as np
    import matplotlib.pyplot as plt
    
    def codeMaker(path,mat,vec):
        
        return """
import bmesh
from mathutils import Vector
with open(r"%s","r") as outf:
	points = [Vector(eval(line.replace("\\n",""))) for line in outf]
	
#Points to mesh
mesh = bpy.data.meshes.new("mesh") 
obj = bpy.data.objects.new("MyObject", mesh)
bpy.context.scene.objects.link(obj)
b = bmesh.new()
for v in points:
	b.verts.new(v)

b.to_mesh(mesh) 
b.free()
C.scene.update()

mat = %s
vec = %s

name = "Bounding_Box"
lattice = bpy.data.lattices.new(name)
lattice_ob = bpy.data.objects.new(name, lattice)
lattice_ob.matrix_world = mat
lattice_ob.scale = (2*vec)[:3]
lattice["Type"] = "MOD3_BoundingBox"
bpy.context.scene.objects.link(lattice_ob)
bpy.context.scene.update()
        """%(path,str(mat),str(vec))
    
    def analyzeFile(path):
        if type(path) is str:
            with open(path,"r") as outf:
            	points = [Vector(eval(line.replace("\n",""))) for line in outf]
        else: points = path
        start = time.time()
        v,e = ConvexHull(points)
        hull = time.time()
        bm,bv = calculateMVBB(v,e)
        end = time.time()
        #print(path)
        #print(bm)
        #print(bv)
        #print()
        #print (codeMaker(path,bm,bv))
        print()
        if type(path) is str:
            print(path)
        print("%d V/%d E on Hull: Hull:%.3f Algo:%.3f Total:%.3f"%(len(v),len(e),hull-start,end-hull,end-start))
        print()
        return len(points),len(v),len(e),hull-start,end-hull,end-start
    
    def analyzeData(data):        
        pointEfficiency =  sorted([(datum[0],datum[5]) for datum in data])
        hullPEfficiency = sorted([(datum[1],datum[5]) for datum in data])
        edgeEfficiency = sorted([(datum[2],datum[5]) for datum in data])
        hullEfficiency = sorted([(datum[0],datum[2]) for datum in data])
        for ix,var in enumerate([pointEfficiency,hullPEfficiency,edgeEfficiency,hullEfficiency]):
            if var:
                x,y = list(zip(*var))[0],list(zip(*var))[1] 
                plt.plot(x,y,"+")
                z = np.polyfit(x,y,3)
                p = np.poly1d(z)
                plt.plot(x,p(x),"r--")
                plt.xlabel(["Point Total","Hull Points","Hull Edges","Point Total"][ix])
                plt.ylabel(["Time","Time","Time","Hull Points"][ix])
                plt.show()
                plt.close()

    def prod(iterable):
        prod = 1
        for i in iterable:
            prod*=i
        return prod

    algorithms = {
                "Recursive Scan":recursiveScan,
                "Diameter First":diameterHeuristic,
                "Minimize Principal":minPrincipal,
                "Maximize Principal":maxPrincipal,
                "Eigenvector Coordinates":allPrincipals,                
                #"Barequet-Har": (lambda x: barequetHar(x,caliper=False)),
                #"Barequet-Har with Caliper": (lambda x:barequetHar(x,caliper=True))
                }

    def analyzeAlgorithmData(data):
        pointEfficiency = [[],[]]
        hullEfficiency = [[],[]]
        edgeEfficiency = [[],[]]
        algorithEfficiency = [[],[]]
        for d in sorted(data,key=lambda x: x["Point Total"]):
            pointEfficiency[0].append(d["Point Total"])
            pointEfficiency[1].append([d[a][0] for a in algorithms])
            hullEfficiency[0].append(d["Hull Points"])
            hullEfficiency[1].append([d[a][0] for a in algorithms])
            edgeEfficiency[0].append(d["Hull Edges"])
            edgeEfficiency[1].append([d[a][0] for a in algorithms])
            algorithEfficiency[0].append(d["Point Total"])
            algorithEfficiency[1].append([d[a][1] for a in algorithms])
        for (x,y),xlabel,ylabel in zip([pointEfficiency,hullEfficiency,edgeEfficiency,algorithEfficiency],
                                        ["Point Total","Hull Points","Hull Edges","Point Total"],
                                        ["Time Taken","Time Taken","Time Taken","Box Volume"]):
            x,y = list(zip(*sorted(zip(x,y))))
            plt.figure(figsize=(16,12))
            plt.plot(x,y,linewidth = 0.5)
            plt.xlabel(xlabel)
            plt.ylabel(ylabel)
            #if ylabel == "Box Volume":
            plt.yscale("log")
            plt.legend(algorithms.keys(),loc="upper left")            
            plt.show()
            plt.close()
            
    def analyzeAlgorithms(points):
        verts,edges = ConvexHull(points)
        data = {"Point Total":len(points),
                "Hull Points":len(verts),
                "Hull Edges":len(edges)}
        for name, algo in algorithms.items():
            #try:
            #print(name)
                start = time.time()
                mat,vec = algo(verts,edges)
                end = time.time()
                timing = end-start
                data[name] = (timing,prod((2*vec)[:3]))
            #except:
            #    print(name)
                #raise e(name)
            #    raise
        return data
    
    data = []
    modellist = list(Path(r"E:\MHW\chunkG0").rglob("*.mod3"))
    #modellist = [Path(r"E:\MHW\chunkG0\Assets\stage\stm410\stm410_018_00\stm410_018_00.mod3")]
    for _ in range(100):
        #try:
            modelIx = random.randint(0,len(modellist)-1)
            modelp = modellist[modelIx]
            #print(model)
            modelfile = FL.FileLike(modelp.open("rb").read())
            model = Mod3()
            model.marshall(modelfile)
            meshes = model.prepareMeshparts(0)
            m = [Vector(v) for v in meshes[random.randint(0,len(meshes)-1)]["vertices"]]
        
            datum = analyzeAlgorithms(m)
            data.append(datum)
        #except Exception as e:
        #    print(modelp)
        #    print(e)
    analyzeAlgorithmData(data)

    #analyzeFile(r"D:\\Downloads\Vertices.txt")    
    #analyzeFile(r"D:\\Downloads\FlatVertices.txt") 
    #analyzeFile(r"D:\\Downloads\FlatOrthoVertices.txt") 
    #analyzeFile(r"D:\\Downloads\SlopedVertices.txt") 
    #analyzeFile(r"D:\\Downloads\LineVertices.txt")
    #analyzeFile(r"D:\\Downloads\ModelVertices.txt")
    #analyzeFile(r"D:\\Downloads\StressTest.txt") 
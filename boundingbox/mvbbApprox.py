# -*- coding: utf-8 -*-
"""
Created on Mon Jun  8 06:19:46 2020

@author: AsteriskAmpersand
"""
import numbers
import numpy as np
from math import sqrt, sin, cos, pi
from mathutils import Vector,Matrix

try:
    from ..boundingbox.msbr import calculateMSBR
    from ..boundingbox.chull import ConvexHull
    from ..boundingbox.linalg import (orthogonalProjection, getCovariance, 
                                        getEigenvectors, completeBasis,
                                        getDimension)
except:
    import sys
    sys.path.insert(0, r'..\boundingbox')
    from msbr import calculateMSBR
    from chull import ConvexHull
    from linalg import (orthogonalProjection, getCovariance, 
                                        getEigenvectors, completeBasis,
                                        getDimension)

class SGrid():
    def __init__(self,intpoints,bbox):
        self.intpoints = intpoints
        self.bbox = bbox
    def diameter(self):
        diam = 0
        i = 0
        j = 0
        hullV,hullE = ConvexHull(self.intpoints)
        for i0 in range(len(hullV)):
            for i1 in range(i0+1,len(hullV)):
                distance = Vector(Vector(hullV[i0])-Vector(hullV[i1])).length*self.bbox.scalar
                if distance > diam:
                    i = i0
                    j = i1
                    diam = distance
        bbox = self.bbox
        return diam, bbox.lookup(hullV[i]),bbox.lookup(hullV[j])
                

class Grid():
    def __init__(self,block):
        self.block = block
    def approximate(self,points):
        intPoints = set([self.block.approximate(p) for p in points])
        return SGrid(intPoints,self.block)
    #G = Grid(eps/(2*sqrt(len(points[0])))*bbox)
    #SG = G.approximate(points)
    #deps,s,t = SG.diameter()#Remove in between points (or along the vertical) and convex hull it when feasible
    #return

class BoundingBox():
    def __init__(self,pointlist = None):
        if pointlist is None:
            self.min = Vector([0,0,0])
            self.max = Vector([0,0,0])
        else:
            self.min = Vector([
                    min(pointlist,key = lambda x: x[0])[0],
                    min(pointlist,key = lambda x: x[1])[1],
                    min(pointlist,key = lambda x: x[2])[2],
                    ])
            self.max = Vector([
                    max(pointlist,key = lambda x: x[0])[0],
                    max(pointlist,key = lambda x: x[1])[1],
                    max(pointlist,key = lambda x: x[2])[2],
                    ])
        self.scalar = 1
        self.reps = {}
        
    def __mul__(self,obj):
        if isinstance(obj,numbers.Number):
            self.scalar = obj
            return self
        
    def __rmul__(self,obj):
        if isinstance(obj,numbers.Number):
            self.scalar = obj
            return self
        
    def approximate(self,point):
        gridpoint = tuple((round(co/self.scalar) for co in point))
        self.reps[gridpoint] = point
        return gridpoint
    
    def lookup(self,coordinates):
        gridpointCandidate = tuple((round(c) for c in coordinates))
        return self.reps[gridpointCandidate]
    
    def to_trans(self):
        return self.scalar*(self.max + self.min)/2
    
    def to_scale(self):
        return self.scalar*(self.max - self.min)
        
def firstApproximateDiameter(points):
    cordwisemax = [points[0]]*len(points[0])
    cordwisemin = [points[0]]*len(points[0])
    for p in points:
        for i in range(len(points[0])):
            if cordwisemin[i][i] > p[i]:
                cordwisemin[i] = p
            if cordwisemax[i][i] < p[i]:
                cordwisemax[i] = p
    sides = [(pMax-pMin).length for pMax,pMin in zip(cordwisemax,cordwisemin)]
    maxcord = np.argmax(sides)
    return (sides[maxcord], 
            [max((c[i] for c in cordwisemax)) for i in range(len(points[0]))], 
            [min((c[i] for c in cordwisemin)) for i in range(len(points[0]))])

def improveDiameterApproximation(points,eps,bbox,diameter):
    G = Grid(eps/(2*sqrt(len(points[0])))*bbox)
    SG = G.approximate(points)
    deps,s,t = SG.diameter()#Remove in between points (or along the vertical) and convex hull it when feasible
    return deps,s,t
    
#2d convex hull can be passed a projection function given a normal vector to the plane
def approximateDiameter(points,eps):
    diamApprox, boxMax, boxMin = firstApproximateDiameter(points)
    diamEps,s,t = improveDiameterApproximation(points,eps,BoundingBox([boxMax,boxMin]),diamApprox)
    return s,t


def inputTransform(points,u,v,w):
    basisChange = Matrix(list(zip(u,v,w))).inverted()
    bb = BoundingBox(list(map(lambda x: basisChange*Vector(x),points)))
    trans = Matrix(list(zip(u,v,w)))*bb.to_trans()
    rotTransMatrix = Matrix(list(zip([*u,0],[*v,0],[*w,0],trans.to_4d())))
    return rotTransMatrix, bb.to_scale() 

def barequetHar(points,eps = None, caliper = False):
    if eps is None:
        eps = 1/sqrt(len(points))
    s,t = approximateDiameter(points,eps)
    v = t-s
    #Option One Approximating Again
    if not caliper:
        Q,cf,_ = orthogonalProjection(points,v,colapse = False)
        sP,tP = approximateDiameter(points,eps)
        vP = tP-sP
        w = v.cross(vP)
    else:
    #Option Two Exact Caliper Found BB for the "Base"
        Q,cf,_ = orthogonalProjection(points,v,colapse = True)
        rot,area,width,height,center_point,corner_points = calculateMSBR(ConvexHull(Q)[0])
        vP = Vector(cf*np.matrix([[cos(rot)],[sin(rot)]]))
        w =  Vector(cf*np.matrix([[cos(rot+pi/2)],[sin(rot+pi/2)]]))
    
    return inputTransform(points,v,vP,w)#matrix

def checkExact(f):
    def projectionChecked(points,edges):
        dim,r,u,v = getDimension(points)
        if dim == -1:
            return Matrix.Identity(4),Vector([0,0,0])
        elif dim == 0:
            v = lambda x,y,z: Vector((x,y,z))
            e1,e2,e3=v(1,0,0),v(0,1,0),v(0,0,1)
            return inputTransform(points,e1,e2,e3)
        elif dim == 1:
            v = completeBasis(u)
            w = u.cross(v)
            return inputTransform(points,u,v,w)
        elif dim == 2:
            return inputTransform(points,u,v.cross(u),v)
        else:
            return f(points,edges)
    return projectionChecked

@checkExact
def allPrincipals(points,edges):
    cov = getCovariance(points)
    ev = getEigenvectors(cov)
    if len(ev) == 1:
        u = ev[0]
        v = completeBasis(u)
        w = u.cross(v)
    elif len(ev) >= 2:
        u = Vector(ev[0])
        v = Vector(ev[1])
        w = u.cross(v)
    else:
        u,v,w = Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))
    return inputTransform(points,u,v,w)
    
def optimizeOnAxis(u,points):
    Q,cf,_ = orthogonalProjection(points,u,colapse = True)
    #print(Q)
    #print(ConvexHull(Q)[0])
    rot,area,width,height,center_point,corner_points = calculateMSBR(ConvexHull(Q)[0])
    v = Vector(cf*np.matrix([[cos(rot)],[sin(rot)]]))
    w =  Vector(cf*np.matrix([[cos(rot+pi/2)],[sin(rot+pi/2)]]))
    return v,w

def extremaPrincipal(points,index):
    hullP,hullE = ConvexHull(points)
    cov = getCovariance(hullP)
    ev = getEigenvectors(cov)
    if len(ev) == 0:
        u,v,w = Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))
    else:
        u = ev[index]
        v,w = optimizeOnAxis(u,hullP)
    return inputTransform(points,u,v,w)

@checkExact
def minPrincipal(points,edges): return extremaPrincipal(points,-1)    
@checkExact
def maxPrincipal(points,edges): return extremaPrincipal(points, 0)   

def diameterScan(points):
    diam = 0
    direction = None
    for p0 in range(len(points)):
        for p1 in range(p0,len(points)):
            if diam < (points[p0]-points[p1]).length:
                diam = (points[p0]-points[p1]).length
                direction = points[p0]-points[p1]
    return direction.normalized()

@checkExact
def diameterHeuristic(points,edges):
    diameter = diameterScan(points)
    u = diameter
    v,w = optimizeOnAxis(u,points)
    return inputTransform(points,u,v,w)

tol = 2*(1-cos(2.5*pi/180))
def projectOptimize(points,basis,i):
    n = basis[(i+1)%3]
    v,w = optimizeOnAxis(n,points)
    v0,w0 = basis[i%3],basis[(i+2)%3]
    difference = abs(1-np.dot(v0,v))+abs(1-np.dot(w0,w))
    if difference<tol:
        return False
    basis[i%3],basis[(i+2)%3] = v,w
    return True

@checkExact
def recursiveScan(points,edges):
    points = np.array(points)
    e1,e2,e3 = np.array((1,0,0)),np.array((0,1,0)),np.array((0,0,1))
    basis = [e1,e2,e3]
    iterations = int(sqrt(len(points)))
    iterations += (-iterations)%3
    for i in range(iterations):
        cont = projectOptimize(points,basis,i)
        if not cont:
            break
    return inputTransform(points,*(map(Vector,basis)))
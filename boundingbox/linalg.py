# -*- coding: utf-8 -*-
"""
Created on Wed Jun 10 18:14:28 2020

@author: AsteriskAmpersand
"""

import numpy as np
from mathutils import Vector,Matrix

def orthogonalProjection(points,n,colapse = False):
    # n . w = 0
    # n0*w0 + n1*w1 + n2*w2 = 0
    u = completeBasis(n)
    if type(n) is np.ndarray:
        n = n*(1/np.linalg.norm(n))
        v = np.cross(n,u)
    else:
        n = n.normalized()
        v = n.cross(u)
    
    A = np.array(list(zip(u,v)))
    AT = A.T
    P = A@np.linalg.inv(AT@A)@AT
    if not colapse:
        projected_Points = [P@point for point in points]
        z = None
        Binv = None
    else:
        B = np.linalg.inv(np.array(list(zip(u,v,n))))
        projected_Points = [Vector((B@P@np.array(point)).tolist()[:2]) for point in points]
        z = (B@np.array(points[0])).tolist()[2]
        Binv = np.array(list(zip(u,v)))
    return projected_Points, Binv, z

def getCovariance(points):
    return np.cov(np.matrix(points).transpose())

def getEigenvectors(matrix):
    lambdas, V =  np.linalg.eig(matrix)
    return [v for l,v in sorted(zip(lambdas,V),key = lambda x: x[0]) if l != 0]  

def completeBasis(n):
    if n[2] == 0: 
        u = Vector((0,0,1))
    else: 
        u = Vector((1,0,n[0]/n[2])).normalized()
    return u

def getLinearVector(points):
    r = points[0]
    vec = None
    for p0 in range(len(points[1:])):
        p = points[p0+1]
        if p != r:
            vec = r-p
            if vec.length != 0:
                vec = None
            else:
                break
    return p0,r,vec

def getNonColinearVector(p0,r,vec,points):
    vec2 = None
    for p in range(p0,len(points[p0:])):
        vec2 = r-points[p]
        #print(vec)
        #print(vec2)
        #print(vec.cross(vec2))
        #print()
        if vec.normalized().dot(vec2.normalized()) != 1:
            return vec2,p
    return None,p

def getDimension(points):
    r,vec,vec2 = None,None,None
    if not len(points):
        dim = -1
    elif len(points) == 1:
        r = points[0]
        dim = 0
    elif len(points) > 1:
        n = len(points)
        r = points[0]
        dim = 0
        for p0 in range(1,n):
            p = points[p0]
            vec0 = p-r
            if not np.linalg.norm(vec0):
                continue
            vec = vec0
            dim = 1
            for p1 in range(p0+1,n):
                p = points[p1]
                vec1 = p-r
                if np.linalg.norm(np.cross(vec,vec1)):
                    vec2 = vec1
                    dim = 2
                    for p2 in range(p1+1,n):
                         vec3 = points[p2]-r
                         if Matrix(list(zip(vec,vec2,vec3))).determinant:
                             dim = 3
                             break
                    break
            break
    return dim,r,vec,vec2
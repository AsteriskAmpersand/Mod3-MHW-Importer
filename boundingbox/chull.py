# -*- coding: utf-8 -*-
"""
Created on Mon Jun  8 21:15:09 2020

@author: AsteriskAmpersand
"""
try:
    import bmesh
    
    def ConvexHull(points):
        if len(points) <= 3:
            return points, []
        b = bmesh.new()
        for v in points:
            b.verts.new(v)
        #print(len(points))
        #print(len(b.verts))
        hull = bmesh.ops.convex_hull(b,input = b.verts)
        g = hull["geom"]
        verts = {obj.index:ix for ix,obj in enumerate([obj for obj in g if type(obj) is bmesh.types.BMVert])}
        edges = [(verts[obj.verts[0].index],verts[obj.verts[1].index]) for obj in g if type(obj) is bmesh.types.BMEdge]
        verts = [obj.co for obj in g if type(obj) is bmesh.types.BMVert]
        return verts,edges
except:
    from pyhull.convex_hull import ConvexHull as CH
    from mathutils import Matrix,Vector
    import numpy as np
    import sys
    sys.path.insert(0, r'..\boundingbox')
    from linalg import (orthogonalProjection,getLinearVector,getNonColinearVector)
    
    def handle1d(points,r,vec):
        m,M = vec.dot(vec),vec.dot(vec)
        minimizer,maximizer = None,None
        for point in points:
            d = (r-point).dot(vec)
            if d <= m:
                minimizer = point
                m = d
            if d >= M:
                maximizer = point
                M = d
        return [minimizer,maximizer],[(0,1)]

    def handle2d(points,vec,vec2):
        n = vec.cross(vec2)
        Q,inv,z = orthogonalProjection(points,n,colapse = True)
        vert,edges = ConvexHull(Q)
        invExt = np.zeros((3,3))
        invExt[:,:-1]=inv
        invExt[:,-1] = np.cross(inv[:,0],inv[:,1])
        vertices = [Vector(invExt@np.array(list(v)+[z])) for v in vert]
        return vertices,edges

    def handleHull(h,points):
        autonumbering = 0
        vert = []
        edges = set()
        scheme = {}
        for vs in h.vertices:
            for v in vs:
                if v not in scheme:
                    scheme[v] = autonumbering
                    vert.append(h.points[v])
                    autonumbering += 1
            for i0,i1 in zip(vs,vs[1:]+vs[0:1]):
                if i0 == i1: continue
                if scheme[i0]==scheme[i1]: continue
                edges.add(tuple(sorted((scheme[i0],scheme[i1]))))
        return vert,list(edges)

    def ConvexHull(points):
        pointset = set()
        for p in points:
            pointset.add(p.freeze() if type(p) is Vector else p)
        points = list(pointset)
        if len(points)<3:
            if len(points) == 2:
                return points,[(0,1)]
            return points,[]
        h = CH(points)
        if not h.vertices:
            p0,r,vec = getLinearVector(points)
            if vec is None:
                return [r],[]
            vec2,p1 = getNonColinearVector(p0,r,vec,points)
            if vec2 is None:
                return handle1d(points,r,vec)
            else:
                return handle2d(points,vec,vec2)
        else:
            return handleHull(h,points)
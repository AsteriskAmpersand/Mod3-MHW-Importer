import numpy as np
from math import cos,sin,pi
from mathutils import Vector, Matrix
try:
    from ..boundingbox.msbr import calculateMSBR
    from ..boundingbox.linalg import orthogonalProjection, getDimension
except:
    import sys
    sys.path.insert(0, r'..\boundingbox')
    from msbr import calculateMSBR
    from linalg import orthogonalProjection, getDimension
#Implemented from https://www.geometrictools.com/Documentation/MinimumVolumeBox.pdf

def calculateMVBB(points,edges):
    if len(points)<4:
        handleDegenerateCases(points,edges)
    # shift the points such that the minimum x, y, z values
    # in the entire set of points is 0.
    points = np.array(points)
    #shift = points.min(axis=0)
    #points = points - shift
    
    min_volume = float("inf")
    n = len(edges)
    specs = None
    # try every pair of edges (ordering is not important)
    for i2 in range(n):
        e2 = edges[i2]
        u2 = points[e2[0]] - points[e2[1]]
        for i1 in range(i2+1,n):  
            e1 = edges[i1]
            u1 = points[e1[0]] - points[e1[1]]
            if np.dot(u2,u1) != 0:
                continue
            # transform the two edges into a orthogonal basis
            u = normcross(u2, u1)
            v = normcross(u, u2)
            w = normcross(u, v)
            
            # project all the points on to the basis u v w
            forward,backwards = basisChange(u, v, w)
            p = points@forward

            volume, mins, maxes = calcVolume(p)
            
            # we are looking for the minimum volume box
            if volume <= min_volume:
                min_volume = volume
                specs = u, v, w, mins, maxes, backwards
    if specs is None:
        return handleDegenerateCases(points,edges)
    u, v, w, mins, maxes, backwards = specs
        
    # get the corner by using our projections, then shift it to move
    # it back into the same origin as the original set of points
    mins = mins.tolist()[0]
    maxes = maxes.tolist()[0]
    corner = u * mins[0] + v * mins[1] + w * mins[2]
    #corner += shift
    
    # create the sides which are vectors with the magnitude the length
    # of that side
    l1 = (maxes[0] - mins[0])
    l2 = (maxes[1] - mins[1])
    l3 = (maxes[2] - mins[2])
    #v1 = u * l1
    #v2 = v * l2
    #v3 = w * l3
    
    #original return corner, v1, v2, v3
    v4 = lambda x: Vector([*x,0])
    vc = Vector((corner + (u*l1+v*l2+w*l3)/2).tolist())
    rotTransMatrix = Matrix(list(zip(v4(u),v4(v),v4(w),
                                vc.to_4d()
                                )))
    return rotTransMatrix, Vector([l1/2,l2/2,l3/2,0]) #matrix
    
def calcVolume(p):
    mins = p.min(axis=0)
    maxes = p.max(axis=0)
    volume = np.prod(maxes - mins)
        
    return volume, mins, maxes  

def basisChange(*vectors):
    return np.linalg.inv(np.matrix(vectors)),np.matrix(vectors) 
    
def normcross(u, v):
    w = np.cross(u, v)
    norm = np.linalg.norm(w)
    if norm:
        w /= norm
    return w
    

def handleDegenerateCases(points,edges):
    dim,r,vec,vec2 = getDimension(points)
    if dim == -1:
        m = Matrix.Identity(4)
        v = Vector((0,0,0,0))
        return m,v
    elif dim == 0:
        m = Matrix.Identity(4)
        m[0][3],m[1][3],m[2][3] = r
        v = Vector((0,0,0,0))
        return m,v
    elif dim == 1:
        return handle1d(points,r,vec)
    elif dim == 2:
        return handle2d(points,r,vec)
    elif dim == 3:
        return handleEdgeBox(points,edges)
    
def handle1d(points,r,vec):
    m,M = vec.dot(vec),vec.dot(vec)
    minimizer,maximizer = None,None
    vec /= vec.length()
    for point in points:
        d = (r-point).dot(vec)
        if d <= m:
            minimizer = point
            m = d
        if d >= M:
            maximizer = point
            M = d
    u = vec
    v = Vector([0,1,0])
    w = u.cross(v)
    mat = Matrix(list(zip([*u,0],[*v,0],[*w,0],[*((maximizer+minimizer)/2),1])))
    return mat, Vector([M-m,0,0,0])

def handleProjective(points,n):
    Q,inv,z = orthogonalProjection(points,n,colapse = True)
    rot, area, width, height, center_point, corner_points = calculateMSBR(Q)
    
    invExt = np.zeros((3,3))
    invExt[:,:-1]=inv
    invExt[:,-1] = np.cross(inv[:,0],inv[:,1])
        
    v = Vector(inv@np.array([[cos(rot)],[sin(rot)]]))
    w =  Vector(inv@np.array([[cos(rot+pi/2)],[sin(rot+pi/2)]]))
    return invExt,z,width,height,center_point,v,w

def handle2d(points,vec,vec2):
    n = vec.cross(vec2)
    invExt,z,width,height,center_point,v,w= handleProjective(points,n)
    center = invExt@np.array(list(center_point)+[z])
    matrix = Matrix(list(zip([*n,0],[*v,0],[*w,0],center.to_4d())))
    vec = Vector([0,width/2,height/2])
    return matrix,vec

def handleEdgeBox(points,edges):
    #Vec proj is dot product divided by norm
    min_vol = float("inf")
    spec = None
    normV = set()
    for e in edges:
        u = Vector(points[e[1]]-points[e[0]]).normalized()
        if tuple(u) in normV:
            continue
        normV.add(tuple(u))
        #print(u)
        invExt,z,width,height,center_point,v,w = handleProjective(points,u)
        pointlen = [np.array(point).dot(u) for point in points]
        m,M = min(pointlen),max(pointlen)
        depth = M-m
        volume = depth*width*height
        center = np.array([*center_point.tolist(),((m+M)/2)])
        uvwCenter = invExt@center
        if volume < min_vol:
            min_vol = volume
            spec = (u, v, w), (uvwCenter.tolist()),(depth,width,height)
                            
    if spec is None:
        raise ValueError("Catastrophic Error")
    (u,v,w),(t0,t1,t2),(depth,width,height) = spec
    matrix = Matrix(list(zip([*u,0],[*v,0],[*w,0],[t0,t1,t2,1])))

    return matrix, Vector([depth/2,width/2,height/2,0]) #matrix
        
    
    
    
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 14 17:20:21 2019

@author: AsteriskAmpersand
"""
from mathutils import Vector
from numpy import angle
from fractions import Fraction


def rationalize(value,N):
    frac = Fraction(value).limit_denominator(N)
    return frac.numerator, frac.denominator

def denormalize(vector):
    x,y,z = vector.x, vector.y, vector.z
    maxima = max(abs(x),abs(y),abs(z))
    x,y,z = round(127*x/maxima), round(127*y/maxima), round(127*z/maxima)
    print(maxima)
    return [x,y,z,0]

def normalize(vecLike):
    vector = Vector(vecLike)
    vector.normalize()
    return vector
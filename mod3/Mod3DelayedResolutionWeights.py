# -*- coding: utf-8 -*-
"""
Created on Sun Mar 31 03:17:56 2019

@author: AsteriskAmpersand
"""

import re
from functools import total_ordering

class UnclassedVertex(Exception):
    pass

@total_ordering
class BufferedWeight():
    weightCaptureGroup = r"(.*)\( *([^,]*) *, *([-+]?[0-9]+) *\)$"
    def __init__(self, weightName,skeletonMap,weightVal):
        if weightName in skeletonMap:
            self.weight = weightVal
            self.boneId = skeletonMap[weightName]
            self.sign = 0
            return
        group = re.match(self.weightCaptureGroup,weightName).group
        weightName = group(1)+group(2)
        weightIndex = int(group(3))
        self.weight = weightVal
        self.boneId = skeletonMap[weightName]
        self.sign = weightIndex == -1
        
            
    def __cmp__(self, bw):
        if self.sign != bw.sign:
            return 1 if self.sign else -1
        if self.boneId == bw.boneId:
            return 0
        else:
            return 1 if self.boneId>bw.boneId else -1
        
    def __eq__(self,bw):
        return self.__cmp__(bw) == 0
        
    def __lt__(self,bw):
        return self.__cmp__(bw) == -1
    
    def execute(self):
        return (self.boneId, self.weight)

class BufferedWeights():
    def __init__(self, bufferedWeightList, errorHandler):
        signed = [w for w in bufferedWeightList if w.sign]
        if len(signed)>1:
            signed = errorHandler.multipleNegativeWeights(signed)
        self.signed = signed
        self.unsigned = [w for w in sorted(bufferedWeightList) if not w.sign]
        self.errorHandler = errorHandler
        self.clasified = False
        
    def __len__(self):
        return len(self.unsigned)+len(self.signed)
        
    weightClasses = {0:0, 1:4,2:4,3:4,5:8,6:8,7:8}
    def weightClass(self):
        self.clasified = True
        category = len(self.unsigned)
        if (category) in self.weightClasses:
            return self.weightClasses[category]
        else:
            if len(self) == 4:
                if self.errorHandler.coerce:
                    self.errorHandler.negativeWeightPrecision(self,4)
                    return 4
            if len(self)>8:
                self.errorHandler.weightCountExceeded(self)
            if len(self) == 8:
                self.errorHandler.negativeWeightPrecision(self,8)
            return 8
    
    def execute(self, weightClass):
        if not self.clasified:
            raise UnclassedVertex
        return [w.execute() for w in self.unsigned] + [(0,0.0) for _ in range(weightClass-len(self))] + [w.execute() for w in self.signed]

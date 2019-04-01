# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 02:25:07 2019

@author: AsteriskAmpersand
"""
try:
    from ..common import Cstruct as CS
except:
    import sys
    sys.path.insert(0, r'..\common')
    import Cstruct as CS

class CMatrix():
    def __init__(self, dimentions):
        self.rowCount = dimentions[0]
        self.columnCount = dimentions[1]
        self.CColMat = CS.Cstruct({"column":"float[%d]"%self.rowCount})
        
    def marshall(self,data):
        #TODO - Sanity check on data dimensions
        return [self.CColMat.marshall(data)["column"] for col in range(self.columnCount)]
    
    def serialize(self, matrix):
        #TODO - Sanity check on data dimensions
        return b''.join([self.CColMat.serialize({"column":col}) for col in matrix])
    
    def __len__(self):
        return self.columnCount*len(self.CColMat)

class Matrix():
    def __init__(self, dimensions, data=None, identity=False):
        self.cMatrix = CMatrix(dimensions)
        self.dimensions = dimensions
        if data == None:
            self.matrix = [[1 if identity and i==j else 0 for j in range(dimensions[0])] for i in range(dimensions[1])]
        else:
            self.marshall(data)
        
    def __add__(self, matrixB):
        #TODO - Sanity check on dimensions of both
        result = Matrix(self.dimensions)
        for row in range(self.dimensions[0]):
            for column in range(self.dimensions[1]):
                result.matrix[column][row] = self.matrix[column][row]+matrixB.matrix[column][row]
        return result
    
    def __sub__(self, matrixB):
        return self + (-matrixB)
    
    def __neg__(self):
        #TODO - Sanity check on dimensions of both
        result = Matrix(self.dimensions)
        for row in range(self.dimensions[0]):
            for column in range(self.dimensions[1]):
                result.matrix[column][row] = -self.matrix[column][row]
        return result  
    
    @staticmethod
    def mul(a,b):
        #TODO - Sanity check on dimensions of both
        c = [[0]*len(a[0]) for _ in range(len(b))]
        for row in range(len(a[0])):
            for column in range(len(b)):
                c[column][row] = sum([a[iteration][row]*b[column][iteration] for iteration in range(len(a[0]))])
        return c
    
    def __mul__(self, matrixB):
        #TODO - Sanity check on dimensions of both
        result = Matrix([self.dimensions[0],matrixB.dimensions[1]])
        result.matrix = Matrix.mul(self.matrix, matrixB.matrix)
        return result
    
    def __rmul__(self, numeric):
        result = Matrix((self.dimensions[0],self.dimensions[1]))
        for row in range(self.dimensions[0]):
            for column in range(self.dimensions[1]):
                result.matrix[column][row] = numeric*self.matrix[column][row]
        return result  
    
    @staticmethod
    def transposeMatrix(m):
        return list(map(list,zip(*m)))
    
    def transpose(self):
        result = Matrix((self.dimensions[1],self.dimensions[0]))
        result.matrix =self.transposeMatrix(self.matrix)
        return result
    
    @staticmethod
    def getMinor(m,i,j):
        return [col[:j] + col[j+1:] for col in (m[:i]+m[i+1:])]
    
    def minor(self, i, j):
        result = Matrix([self.dimensions[0]-1,self.dimensions[1]-1])
        result.matrix = self.getMinor(self.matrix,i,j)
        return result
    
    @staticmethod
    def getDeterminant(m):
        #base case for 2x2 matrix
        if len(m) == 2:
            return m[0][0]*m[1][1]-m[0][1]*m[1][0]
    
        determinant = 0
        for c in range(len(m)):
            determinant += ((-1)**c)*m[0][c]*Matrix.getDeterminant(Matrix.getMinor(m,0,c))
        return determinant
    def det(self):
        return self.getDeterminant(self.matrix)
        
    @staticmethod
    def getInverse(m):
        determinant = Matrix.getDeterminant(m)
        #special case for 2x2 matrix:
        if len(m) == 2:
            return [[m[1][1]/determinant, -1*m[0][1]/determinant],
                    [-1*m[1][0]/determinant, m[0][0]/determinant]]
    
        #find matrix of cofactors
        cofactors = []
        for r in range(len(m)):
            cofactorRow = []
            for c in range(len(m)):
                minor = Matrix.getMinor(m,r,c)
                cofactorRow.append(((-1)**(r+c)) * Matrix.getDeterminant(minor))
            cofactors.append(cofactorRow)
        cofactors = Matrix.transposeMatrix(cofactors)
        for r in range(len(cofactors)):
            for c in range(len(cofactors)):
                cofactors[r][c] = cofactors[r][c]/determinant
        return cofactors
    def invert(self):
        result = Matrix(self.dimensions)
        result.matrix = Matrix.getInverse(self.matrix)
        return result

    def __mod__(self, matrixB):
        """Hadamard Product of Matrices"""
        #TODO - Sanity check on dimensions of both
        result = Matrix(self.dimensions)
        for row in range(self.dimensions[0]):
            for column in range(self.dimensions[1]):
                result.matrix[column][row] = self.matrix[column][row]*matrixB.matrix[column][row]
        return result
    
    def column(self, index):
        C = Matrix([self.dimensions[0],1])
        C.matrix = [self.matrix[index]]#[[self.matrix[index][j] for j in range(self.dimensions[0])]]
        return C
    
    def position(self, x,y,z):
        for i,w in enumerate([x,y,z]):
            self.matrix[i][3]=w
        return self
    
    def AMatFromLMat(self,LMat):
        try:
            A = Matrix(self.dimensions)
            A.matrix = Matrix.getInverse(self.minor(3,3).matrix)
        except:
            for i in range(self.dimensions[0]):
                A.matrix[i][i]=1
        C = LMat.minor(3,3)
        D =  LMat.minor(0,3).column(2)
        self.matrix[self.dimensions[0]-1] = [A*C*D]+[self.matrix[self.dimensions[0]-1][self.dimensions[1]-1]]
        return self
        
    
    def marshall(self,data):
        self.matrix = self.cMatrix.marshall(data)
        
    def construct(self, matrix):
        self.matrix = [[matrix[row][col] for row in range(self.dimensions[0])] for col in range(self.dimensions[1])]
        
    def serialize(self):
        return self.cMatrix.serialize(self.matrix)
    
    def verify(self):
        if len(self.matrix)!=self.dimensions[1] or \
            (self.matrix and len(self.matrix[0]) != self.dimensions[0]) or\
            (self.matrix and any([len(self.matrix[0])!=len(self.matrix[j]) for j in range(len(self.matrix))])):
            raise AssertionError("Matrix has illegal dimensions.")
    
    def __len__(self):
        return len(self.cMatrix)
    
    def __eq__(self, matrix):
        return self.matrix == matrix.matrix
    
    def columnRepresentation(self):
        return self.matrix
    
    def maxima(self):
        return max(map(max, self.matrix))
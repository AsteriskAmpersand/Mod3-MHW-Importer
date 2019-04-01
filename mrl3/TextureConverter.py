# -*- coding: utf-8 -*-
"""
Created on Wed Mar 13 00:18:07 2019

@author: AsteriskAmpersand
"""
import sys
import os
import subprocess

if sys.platform.startswith("win"):
    # Don't display the Windows GPF dialog if the invoked program dies.
    # See comp.os.ms-windows.programmer.win32
    #  How to suppress crash notification dialog?, Jan 14,2004 -
    #     Raymond Chen's response [1]

    import ctypes
    SEM_NOGPFAULTERRORBOX = 0x0002 # From MSDN
    ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX);
    CREATE_NO_WINDOW = 0x08000000    # From Windows API
    subprocess_flags = CREATE_NO_WINDOW
else:
    subprocess_flags = 0
    

def convertTexToDDS(path):
    processLocation = os.path.join(os.path.dirname(__file__),"MHWorldTex.exe")
    FNULL = open(os.devnull, 'w')
    args = "\"" + processLocation + "\"" + " \"" + path + "\""
    try:
        subprocess.check_output(args, stdin=FNULL, stderr=FNULL, shell=False, creationflags=subprocess_flags)
    except:
        pass
    
def convertDDSToPNG(path):
    processLocation = os.path.join(os.path.dirname(__file__),"TexConv.exe")
    FNULL = open(os.devnull, 'w')
    args = "\"" + processLocation + "\"" + " \"" + path + "\"" +" -ft png -o \""+os.path.dirname(path)+ "\""
    try:
        subprocess.check_output(args, stdin=FNULL, stderr=FNULL, shell=False, creationflags=subprocess_flags)
    except:
        pass
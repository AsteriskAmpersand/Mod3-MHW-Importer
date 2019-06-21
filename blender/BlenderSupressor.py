import os
import sys

class SupressBlenderOps():
    def __init__(self):
        pass
    def __enter__(self):
            open(os.devnull, 'a').close()
            self.old = os.dup(1)
            sys.stdout.flush()
            os.close(1)
            os.open(os.devnull, os.O_WRONLY)
    def __exit__(self, *args):
            os.close(1)
            os.dup(self.old) # should dup to 1
            os.close(self.old)   
            return False
            
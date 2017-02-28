import os.path, imp, shutil, tempfile, os
import backports.lzma as lzma

##
## lzma utils
##

def lzd (src, tgt) :
    with lzma.open(src, "rb") as srcfile :
        with open(tgt, "wb") as tgtfile :
            tgtfile.write(srcfile.read())

def lzc (src, tgt) :
    with open(src, "rb") as srcfile :
        with lzma.open(tgt, "wb") as tgtfile :
            tgtfile.write(srcfile.read())

class lzuse (object) :
    def __init__ (self, path, name=None, link=True, chdir=True) :
        if name is None :
            name = os.path.splitext(os.path.basename(path))[0]
        self.name = name
        self.root = tempfile.mkdtemp()
        self.path = os.path.join(self.root, name)
        self.back = os.getcwd()
        self.clean = False
        lzd(path, self.path)
        if link :
            os.symlink(os.path.join(self.back, "medusa"),
                       os.path.join(self.root, "medusa"))
        if chdir :
            os.chdir(self.root)
        else :
            self.back = None
    def _clear (self) :
        if not self.clean :
            if self.back is not None :
                os.chdir(self.back)
            shutil.rmtree(self.root)
            self.clean = True
    def __enter__ (self) :
        return self
    def __exit__ (self, exc_type, exc_val, exc_tb) :
        self._clear()
    def __del__ (self) :
        self._clear()

def lzimport (path) :
    with lzuse(path, link=True, chdir=True) as tmp :
        with open(tmp.path) as src :
            return imp.load_source(tmp.name.split(".", 1)[0], tmp.name, src)

def lznet (path) :
    return lzimport(path).net

def lzread (path) :
    with lzuse(path, link=False, chdir=False) as tmp :
        with open(tmp.path) as src :
            return src.read()

def lzwrite(data, path) :
    with lzma.open(path, "wb") as outfile :
        outfile.write(data)

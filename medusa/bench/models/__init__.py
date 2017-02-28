import re, time, hashlib, bz2

import snakes.plugins
import medusa.faster as faster
snakes.plugins.load(["labels", faster], "snakes.nets", "snk")
from snk import *
from snakes.data import cross

def guard (timeout) :
    data = start = time.time()
    while time.time() - start < timeout :
        data = bz2.compress(hashlib.sha512(str(data)).hexdigest(), 9)
    return True

_filename = re.compile("[^a-z0-9_]+", re.I)

class Model (object) :
    params = {"chroma" : (0, 10)}
    def __init__ (self, **params) :
        self.attr = []
        for key, boundaries in sorted(self.params.items()) :
            val = params.pop(key, boundaries[0])
            setattr(self, key, val)
            self.attr.append("%s=%s" % (key, val))
        if params :
            raise TypeError("unexpected parameters: %s" % ", ".join(params.keys()))
        self.guard = "guard(%s)" % (self.chroma / 10.0)
        self.net = PetriNet("%s+%s" % (self.__class__.__name__, "+".join(self.attr)))
        self.net.label(**params)
        self.net.globals["guard"] = guard
        self.name = _filename.sub("_", self.net.name).lower()
    @classmethod
    def cases (cls) :
        keys = []
        ranges = []
        for key, boundaries in sorted(cls.params.items()) :
            keys.append(key)
            if len(boundaries) == 2 :
                start, stop = boundaries
                step = 1
            elif len(boundaries) == 3 :
                start, stop, step = boundaries
            ranges.append(range(start, stop+1, step))
        for x in cross(ranges) :
            yield cls(**dict(zip(keys, x)))
    def __repr__ (self) :
        return "%s(%s)" % (self.__class__.__name__, ", ".join(self.attr))
    def tikz (self, out=None, **options) :
        if out is None :
            out = open("%s.tikz" % self.name, "w")
        out.write(r"\begin{tikzpicture}[%s]"
                  % ",".join("%s=%s" % kv for kv in options.items()) + "\n")
        node = {}
        for i, p in enumerate(self.net.place()) :
            n = node[p.name] = "p%s" % i
            pos, txt = self.tikz_place(p)
            out.write(r"  %% %s" % p.name + "\n")
            out.write(r"  \node[place] (%s) at (%s) {};"  % (n, pos) + "\n")
            out.write(r"  \node at (%s) {%s};"  % (n, txt) + "\n")
        for i, t in enumerate(self.net.transition()) :
            n = node[t.name] = "t%s" % i
            pos, txt = self.tikz_trans(t)
            out.write(r"  %% %s" % t.name + "\n")
            out.write(r"  \node[trans] (%s) at (%s) {};"  % (n, pos) + "\n")
            out.write(r"  \node at (%s) {%s};"  % (n, txt) + "\n")
        out.write(r"  \begin{pgfonlayer}{bg}" + "\n")
        for t in self.net.transition() :
            for p, a in t.input() :
                pts = (["(%s)" % node[p.name]]
                       + list(self.tikz_input(p, t))
                       + ["(%s)" % node[t.name]])
                out.write(r"  \draw[arc] " + " -- ".join(pts) + ";\n")
            for p, a in t.output() :
                pts = (["(%s)" % node[t.name]]
                       + list(self.tikz_output(p, t))
                       + ["(%s)" % node[p.name]])
                out.write(r"  \draw[arc] " + " -- ".join(pts) + ";\n")
        out.write(r"  \end{pgfonlayer}" + "\n")
        out.write(r"\end{tikzpicture}")
    def tikz_place (self, place) :
        pos = ",".join(str(p) for p in place.label("pos"))
        if place.tokens :
            return pos, r"$\bullet$"
        else :
            return pos, ""
    def tikz_trans (self, trans) :
        pos = ",".join(str(p) for p in trans.label("pos"))
        return pos, ""
    def tikz_input (self, place, trans) :
        return []
    def tikz_output (self, place, trans) :
        return []
    def nd (self, out=None) :
        if out is None :
            out = open("%s.net" % self.name, "w")
        out.write("net {%s}\n" % self.net.name)
        for p in self.net.place() :
            out.write("pl {%s} (%s)\n" % (p.name, len(p.tokens)))
        for t in self.net.transition() :
            out.write("tr {%s}" % t.name)
            for p, a in t.input() :
                out.write(" {%s}" % p.name)
            out.write(" ->")
            for p, a in t.output() :
                out.write(" {%s}" % p.name)
            out.write("\n")

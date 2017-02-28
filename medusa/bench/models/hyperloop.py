from medusa.bench.models import *

##
## hyperloop
##

class HyperLoop (Model) :
    params = {"chroma" : (0, 10, 1),
              "width"  : (2, 11, 1),
              "dim"    : (2, 11, 1)}
    def trans (self, coords, dim) :
        return "t[%s]%s" % (",".join(str(c) for c in coords), dim)
    def place (self, coords) :
        return "p[%s]" % (",".join(str(c) for c in coords))
    def build (self) :
        ids = list(cross([range(self.width) for d in range(self.dim)]))
        for coords in ids :
            p = Place(self.place(coords), [] if coords[0] else [dot])
            p.label(pos=list(coords))
            self.net.add_place(p)
            for d in range(self.dim) :
                t = Transition(self.trans(coords, d), Expression(self.guard))
                c = list(coords)
                c[d] += .5
                t.label(pos=c, coords=coords, dim=d)
                self.net.add_transition(t)
                self.net.add_input(p.name, t.name, Value(dot))
        for t in self.net.transition() :
            d = t.label("dim")
            succ = list(t.label("coords"))
            succ[d] = (succ[d] + 1) % self.width
            self.net.add_output(self.place(succ), t.name, Value(dot))
    def tikz (self, out=None, **options) :
        if "scale" not in options :
            options["scale"] = 5
        Model.tikz(self, out, **options)
    def tikz_output (self, place, trans) :
        dim = trans.label("dim")
        if trans.label("pos")[dim] > place.label("pos")[dim] :
            if dim == 0 :
                a = trans.label("pos")
                a[0] -= .25
                a[1] += .1
                yield "(%s)" % ",".join(str(x) for x in a)
                b = [.25, a[1]] + a[2:]
                yield "(%s)" % ",".join(str(x) for x in b)
            elif dim == 1 :
                a = trans.label("pos")
                a[0] += .08
                a[1] -= .25
                yield "(%s)" % ",".join(str(x) for x in a)
                b = [a[0], .25] + a[2:]
                yield "(%s)" % ",".join(str(x) for x in b)
            elif dim == 2 :
                a = trans.label("pos")
                a[0] += .07
                a[1] += .25
                yield "(%s)" % ",".join(str(x) for x in a)
                b = place.label("pos")
                b[0] -= .25
                b[1] -= .07
                yield "(%s)" % ",".join(str(x) for x in b)

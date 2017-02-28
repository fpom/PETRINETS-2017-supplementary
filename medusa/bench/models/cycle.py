from medusa.bench.models import *

##
## cycle
##

class Cycle (Model) :
    params = {"chroma" : (0, 10, 1),
              "tokens" : (1, 10, 1),
              "length" : (3, 1010, 10)}
    def build (self) :
        angle = 180.0 / self.length
        for i in range(self.length) :
            p = Place("p[%s]" % i, [dot] if i < self.tokens else [])
            p.label(pos=angle*2*i)
            self.net.add_place(p)
            t = Transition("t[%s]" % i, Expression(self.guard))
            t.label(pos=angle*(2*i+1))
            self.net.add_transition(t)
        for i in range(self.length) :
            self.net.add_input("p[%s]" % i, "t[%s]" % i, Value(dot))
            self.net.add_output("p[%s]" % ((i+1) % self.length), "t[%s]" % i, Value(dot))
    def tikz (self, out=None, **options) :
        # TODO: compute scale to optimise the distance between node
        if "scale" not in options :
            options["scale"] = 5
        Model.tikz(self, out, **options)
    def tikz_place (self, place) :
        pos = "%s:1" % place.label("pos")
        if place.tokens :
            return pos, r"$\bullet$"
        else :
            return pos, ""
    def tikz_trans (self, trans) :
        return "%s:1" % trans.label("pos"), ""

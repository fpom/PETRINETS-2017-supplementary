from medusa.bench.models import *

##
## starsflower
##

class StarFlower (Model) :
    params = {"chroma" : (0, 10, 1),
              "num"    : (2, 20, 1),
              "depth"  : (1, 10, 1)}
    def build (self) :
        def layer (d) :
            if d == 0 :
                for a in range(self.num) :
                    p = Place("p[%s:0]" % a, [dot])
                    p.label(angle=a*(360.0/self.num), depth=1)
                    self.net.add_place(p)
            for a in range(self.num) :
                r = Transition("r[%s:%s]" % (a, d), Expression(self.guard))
                r.label(angle=a*(360.0/self.num), depth=2*d+2)
                self.net.add_transition(r)
                self.net.add_output("p[%s:%s]" % (a, d), r.name, Value(dot))
                x = Place("p[%s:%s]" % (a, d+1))
                x.label(angle=a*(360.0/self.num), depth=2*d+3)
                self.net.add_place(x)
                self.net.add_input(x.name, r.name, Value(dot))
            s = 180.0/self.num
            for a in range(self.num) :
                t = Transition("t[%s:%s]" % (a, d), Expression(self.guard))
                t.label(angle=s+a*(360.0/self.num), depth=2*d+2)
                self.net.add_transition(t)
                self.net.add_input("p[%s:%s]" % (a, d), t.name, Value(dot))
                self.net.add_input("p[%s:%s]" % ((a+1) % self.num, d), t.name, Value(dot))
                self.net.add_output("p[%s:%s]" % (a, d+1), t.name, Value(dot))
                self.net.add_output("p[%s:%s]" % ((a+1) % self.num, d+1), t.name, Value(dot))
        for d in range(self.depth) :
            layer(d)
    def tikz_place (self, place) :
        pos = "%s:%s" % (place.label("angle"), place.label("depth"))
        if place.tokens :
            return pos, r"$\bullet$"
        else :
            return pos, ""
    def tikz_trans (self, trans) :
        pos = "%s:%s" % (trans.label("angle"), trans.label("depth"))
        return pos, ""

from medusa.bench.models import *

##
## parallel
##

class Parallel (Model) :
    params = {"chroma" : (0, 10, 1),
              "length" : (10, 1010, 10)}
    def build (self) :
        for i in range(self.length) :
            p = Place("p[%s]" % i, [dot])
            p.label(pos=i)
            self.net.add_place(p)
            t = Transition("t[%s]" % i, Expression(self.guard))
            t.label(pos=i)
            self.net.add_transition(t)
            self.net.add_input("p[%s]" % i, "t[%s]" % i, Value(dot))
            self.net.add_output("p[%s]" % i, "t[%s]" % i, Value(dot))
    def tikz_place (self, place) :
        return "%s,0" % place.label("pos"), r"$\bullet$"
    def tikz_trans (self, trans) :
        return "%s,1" % trans.label("pos"), ""

from snakes.hashables import hset, hdict
from medusa.game import Player as MedusaPlayer

class Struct (hdict) :
    _fields = []
    def __init__ (self, *l, **k) :
        assert set(k) <= set(self._fields), "invalid field"
        d = dict(zip(self._fields, l))
        assert not (set(d) & set(k)), "duplicate field"
        d.update(k)
        hdict.__init__(self, d)
    def __getattr__ (self, name) :
        return self[name]
    def __call__ (self, **fields) :
        f = dict(self)
        f.update(fields)
        return self.__class__(**f)
    def __str__ (self) :
        return "{" + ", ".join("%s: %s" % (k, self[k]) for k in self._fields) + "}"
    def __repr__ (self) :
        return self.__str__()

net = None

class Flow (Struct) :
    _fields = ["sub", "add"]
    def __str__ (self) :
        return "-%s+%s" % (self.sub, self.add)

def getflows (trans, marking) :
    net.set_marking(marking)
    t = net.transition(trans)
    return tuple(Flow(*t.flow(m)) for m in t.modes())

class Trace (Struct) :
    _fields = ["state"]
    def __init__ (self, *l) :
        if not l :
            #l = ["init", net.get_marking()]
            l = [net.get_marking()]
        Struct.__init__(self, *l)
    def __str__ (self) :
        # return "%s => %s" % (self.trans, self.state)
        return str(self.state)
    def filter (self, flows) :
        ret = tuple(f for f in flows if f.sub <= self.state)
        if len(ret) == 0 :
            return None
        elif len(ret) == 1 :
            return ret[0]
        raise Exception("non-deterministic transition")

# player structure

class Player (Struct) :
    _fields = ["trans", "state", "retry", "team", "out"]
    def __str__ (self) :
        if self.retry :
            return "%s[retry]" % self.trans
        else :
            return "%s[%s]" % (self.trans, self.state)
    @classmethod
    def init (cls) :
        players = MedusaPlayer.build(net, None)
        for p in players :
            yield cls(trans=p.name,
                      retry=False,
                      state="call",
                      team=hset(q.name for q in p.team),
                      out=hset(q.name for q in p.out))
    @classmethod
    def find (cls, name, players) :
        for p in players :
            if p.trans == name :
                return p
    @classmethod
    def fire (cls, main, players) :
        for p in players :
            if p.trans not in main.team | main.out :
                yield p()
            elif p == main or p.state == "idle" :
                yield p(state="call")
            elif p.state == "busy" and p.trans in main.out :
                yield p(retry=True)
            else :
                yield p()

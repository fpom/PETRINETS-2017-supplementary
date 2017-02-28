import collections, time, psutil, sys, re, ast, inspect
import numpy.random as random
import gevent
import snakes.lang

from medusa.async import call, ServerPool, gipc
import medusa.log as log

##
## just a bit of metaprogramming
##

PRAGMAS = {"STATS"  : True,
           "LOGS"   : True,
           "CHECKS" : False,
           "BENCHS" : True,
           "FAIR"   : False}

if PRAGMAS["BENCHS"] :
    PRAGMAS["STATS"] = True

_pragmas = re.compile("^((%s)_)+" % "|".join(PRAGMAS))

class Patcher (ast.NodeTransformer) :
    def __init__ (self, lineshift) :
        ast.NodeTransformer.__init__(self)
        self.lineshift = lineshift
    def generic_visit (self, node) :
        if hasattr(node, "lineno") :
            node.lineno += self.lineshift
        return ast.NodeTransformer.generic_visit(self, node)
    def visit_If (self, node) :
        try :
            code = compile(ast.Expression(body=node.test),
                           "<test:%s>" % node.lineno, "eval")
            test = eval(code, {"PRAGMAS" : PRAGMAS.copy()})
        except :
            test = False
        if test :
            return [self.generic_visit(n) for n in node.body]
        elif "PRAGMAS" in snakes.lang.unparse(node.test) :
            return None
        return self.generic_visit(node)
    def visit_FunctionDef (self, node) :
        match = _pragmas.match(node.name)
        if match :
            if any(PRAGMAS[p] for p in node.name[0:match.end()].split("_") if p) :
                node.name = node.name[match.end():]
            else :
                return None
        return self.generic_visit(node)

_patched = []

def patch (cls) :
    _patched.append(cls)
    src, pos = inspect.getsourcelines(cls)
    ind = len(src[0]) - len(src[0].lstrip())
    src = "".join(l[ind:] for l in src)
    patch = Patcher(pos)
    tree = patch.visit(ast.parse(src, "<string>"))
    env = globals().copy()
    exec snakes.lang.unparse(tree) in env
    return env[cls.__name__]

def repatch () :
    global _patched
    p, _patched = _patched, []
    env = globals()
    for cls in p :
        env[cls.__name__] = patch(cls)
    if PRAGMAS["BENCHS"] :
        PRAGMAS["STATS"] = True

@patch
class PatchTest (object) :
    if PRAGMAS["STATS"] :
        count = 0
    def __init__ (self, message) :
        if PRAGMAS["STATS"] :
            self.__class__.count += 1
            message = "[%s] %s" % (self.count, message)
        self.message = message
    def __str__ (self) :
        parts = []
        if PRAGMAS["STATS"] :
            parts.append("STATS")
        if PRAGMAS["LOGS"] :
            parts.append("LOGS")
        if PRAGMAS["BENCHS"] :
            parts.append("BENCHS")
        if PRAGMAS["CHECKS"] :
            parts.append("CHECKS")
        return "%s (%s)" % (self.message, ", ".join(parts))

# if __name__ == "__main__" :
#     print PatchTest("hello world")
#     print PatchTest("bye bye")
#     sys.exit(0)

##
## execution engine
##

class flow (object) :
    def __init__ (self, sub, add) :
        self.sub = sub
        self.add = add
    def __repr__ (self) :
        return "-%s+%s" % (self.sub, self.add)

@patch
class Net (ServerPool) :
    "Perform net-related computations in remote processes"
    def __init__ (self, count, net) :
        ServerPool.__init__(self, count, net=net)
        if PRAGMAS["STATS"] :
            self.stats = collections.defaultdict(int)
    def getflows (self, trans, marking) :
        return self.call(trans, marking)
    def proceed (self, trans, marking) :
        self.net.set_marking(marking)
        t = self.net.transition(trans)
        return [flow(*t.flow(m)) for m in t.modes()]
    def STATS_call (self, *l, **k) :
        start = time.time()
        pipe = self.getpipe()
        self.stats["wait"] += time.time() - start
        try :
            pipe.put((l, k, time.time()))
        except gipc.GIPCClosed :
            # end of simulation
            gevent.getcurrent().kill()
        try :
            resp, ipc, comp, start = pipe.get()
        except EOFError :
            # end of simulation
            gevent.getcurrent().kill()
        self.stats["ipc"] += time.time() - start
        self.stats["comp"] += comp
        self.stats["count"] += 1
        self.putpipe(pipe)
        if isinstance(resp, Exception) :
            raise resp
        else :
            return resp
    def STATS_remote (self, pipe, num, args) :
        self.init(num, args)
        while True :
            try :
                l, k, start = pipe.get()
            except EOFError :
                break
            ipc = time.time() - start
            try :
                start = time.time()
                resp = self.proceed(*l, **k)
                comp = time.time() - start
            except Exception as err :
                resp = err
            pipe.put((resp, ipc, comp, time.time()))
        pipe.close()

@patch
class Trace (object) :
    "Dummy trace object"
    def __init__ (self, net) :
        self.last = net.get_marking()
        if PRAGMAS["LOGS"] :
            log.info("init with %s" % self.last)
        if PRAGMAS["STATS"] :
            self.stats = collections.defaultdict(int)
            self.count = 0
        if PRAGMAS["CHECKS"] :
            self.net = net
        if PRAGMAS["FAIR"] :
            self.trans = collections.defaultdict(int)
    def fire (self, trans, succ) :
        "Extend the trace with an event"
        if PRAGMAS["LOGS"] :
            log.info("fire %s:  %s => %s" % (trans, self.last, succ))
        if PRAGMAS["CHECKS"] :
            pred = self.last
        self.last = succ
        if PRAGMAS["STATS"] :
            self.count += 1
        if PRAGMAS["FAIR"] :
            self.trans[trans] += 1
        if PRAGMAS["CHECKS"] :
            self.net.set_marking(pred)
            for t in self.net.transition() :
                for m in t.modes() :
                    t.fire(m)
                    if t.name == trans and self.net.get_marking() == succ :
                        return
                    self.net.set_marking(pred)
            log.err("invalid firing of %s => %s (does not exist)"
                    % (trans, succ))
            self.netserver.kill()
            sys.exit(0)

BUSY = "busy"
IDLE = "idle"

@patch
class Player (object) :
    if PRAGMAS["STATS"] :
        interval = 2
    def __init__ (self, name, net, trace) :
        self.name = name
        self.net = net
        self.trace = trace
        self.out = set()
        self.team = set()
        self.retry = False
        self.state = IDLE
    def __str__ (self) :
        return "player[%s]" % self.name
    @classmethod
    def build (cls, net, netserver) :
        cls.trace = trace = Trace(net)
        cls.net = trace.netserver = netserver
        trans = dict((t.name, cls(t.name, netserver, trace))
                     for t in net.transition())
        if PRAGMAS["LOGS"] :
            log.build("players = " + ", ".join(sorted(trans)))
        for name, player in trans.items() :
            for out in set(t for p in net.post(name) for t in net.post(p)) :
                player.out.add(trans[out])
            if PRAGMAS["LOGS"] :
                log.build("%s -> %s"
                          % (player, ", ".join(str(t) for t in player.out)))
        allgroups = set(frozenset(net.post(place.name)) for place in net.place())
        for num, transitions in enumerate(allgroups) :
            group = [trans[t] for t in transitions]
            for player in group :
                player.team.update(group)
        players = trans.values()
        if PRAGMAS["LOGS"] :
            for player in players :
                log.build("%s => team %s" % (player, ", ".join(str(p.name)
                                                               for p in player.team)))
        return players
    @classmethod
    def simul (cls, net, nprocs=4, timeout=None) :
        netserver = Net(nprocs, net)
        players = cls.build(net, netserver)
        if PRAGMAS["LOGS"] :
            log.info("start simulation for %r" % net.name)
        cls.startup(players)
        if timeout :
            gevent.sleep(timeout)
            if PRAGMAS["FAIR"] :
                print "fairness:", dict(players[0].trace.trans)
            if PRAGMAS["CHECKS"] :
                players[0].reportstat()
            if PRAGMAS["BENCHS"] :
                print "bench:", cls.reportstat()
            netserver.kill()
            gevent.sleep(1)
            sys.exit(0)
    @classmethod
    def startup (cls, players) :
        if PRAGMAS["STATS"] :
            cls.start = time.time()
            cls.procs = [psutil.Process()] + [psutil.Process(pid)
                                              for pid in players[0].net.pids]
            cls.pool = len(cls.procs)
            for p in cls.procs :
                p.cpu_percent()
        if PRAGMAS["LOGS"] :
            log.players = list(sorted(p.name for p in players))
        for p in random.permutation(players) :
            p.state = BUSY
            call(p.work)
        if PRAGMAS["STATS"] :
            cls._loopstat = gevent.spawn(players[0].loopstat)
    def STATS_loopstat (self) :
        while True :
            gevent.sleep(self.interval)
            try :
                self.reportstat()
            except :
                pass
    def work (self) :
        self.retry = False
        marking = self.trace.last
        if PRAGMAS["LOGS"] :
            log.debug(self, ">> flows(%s)" % marking)
        flows = self.net.getflows(self.name, marking)
        if PRAGMAS["LOGS"] :
            log.debug(self, "<< flows(%s) = %s" % (marking, flows))
        flows = [f for f in flows if f.sub <= self.trace.last]
        if PRAGMAS["LOGS"] :
            log.debug(self, ".. keep %s" % flows)
        if self.retry and not flows :
            call(self.work)
            if PRAGMAS["LOGS"] :
                log.debug(self, "=> %sretry" % log.YELLOW)
            if PRAGMAS["STATS"] :
                self.net.stats["retries"] += 1
            return
        if not flows :
            self.state = IDLE
            if PRAGMAS["LOGS"] :
                log.debug(self, "=> %ssleep" % log.YELLOW)
        else :
            flow = random.choice(flows)
            if PRAGMAS["LOGS"] :
                log.debug(self, "=> %sfire with %s" % (log.YELLOW, flow))
            try :
                succ = self.trace.last - flow.sub + flow.add
            except Exception as err :
                if PRAGMAS["LOGS"] :
                    log.debug(self, "fire failed!")
                    log.err("%s - %s + %s => %s"
                            % (self.trace.last, flow.sub, flow.add, err))
                self.net.kill()
                sys.exit(0)
            self.trace.fire(self.name, succ)
            self.state = IDLE
            for player in random.permutation(list(self.team | self.out)) :
                if player.state == IDLE :
                    if PRAGMAS["LOGS"] :
                        log.debug(self, "=> call %s.work" % player.name)
                    player.state = BUSY
                    call(player.work)
                elif player.state == BUSY :
                    if PRAGMAS["LOGS"] :
                        log.debug(self, ".. skip %s (%s)" % (player.name, player.state))
                    if player in self.out :
                        player.retry = True
                else :
                    pass
                    if PRAGMAS["LOGS"] :
                        log.debug(self, ".. skip %s (%s)" % (player.name, player.state))
    @classmethod
    def STATS_reportstat (cls) :
        clock_time = time.time() - cls.start
        stats = {"procs" : len(cls.procs),
                 "rate" : cls.trace.count / clock_time,
                 "retries" : cls.net.stats["retries"],
                 "events" : cls.trace.count,
                 "clock_time" : clock_time,
                 "cpu_time" : sum(sum(p.cpu_times()) for p in cls.procs),
                 "cpu_usage" : sum(p.cpu_percent() / 100.0 for p in cls.procs),
                 "ipc_count" : cls.net.stats["count"],
                 "ipc_wait" : cls.net.stats["wait"],
                 "ipc_io" : cls.net.stats["ipc"],
                 "ipc_compute" : cls.net.stats["comp"]}
        if PRAGMAS["LOGS"] :
            log.stat("[%(procs)u] %(events)u in %(clock_time).1fs => %(rate).1ff/s"
                     " | %(retries)u retries"
                     " | %(ipc_count)u IPC (w=%(ipc_wait).1f, io=%(ipc_io).1f,"
                     " c=%(ipc_compute).1f)" % stats)
        return stats

##
## main
##

if __name__ == "__main__" :
    import medusa.bench.io as io
    log.verbosity = log.ERROR | log.WARN | log.STAT #| log.BUILD #| log.INFO #| log.DEBUG
    try :
        path, procs, timeout = sys.argv[1:4]
        procs = int(procs)
        timeout = float(timeout)
        try :
            pragmas = sys.argv[4]
            names = re.split("[+-]", pragmas)[1:]
            signs = re.split("[^+-]+", pragmas)[:-1]
            for s, n in zip(signs, names) :
                assert n in PRAGMAS, "invalid pragma %r" % n
                PRAGMAS[n] = (s == "+")
            repatch()
        except IndexError :
            pass
        except AssertionError as err :
            print err
            raise
    except :
        print "Usage: python medusa/engine.py NETFILE PROCS TIMEOUT [PRAGMAS]"
        sys.exit(1)
    if path.endswith(".py") :
        execfile(path)
    elif path.endswith(".py.xz") :
        net = io.lznet(path)
    else :
        print "Cannot load %r" % path
        sys.exit(2)
    Player.simul(net, procs, timeout)

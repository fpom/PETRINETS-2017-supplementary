import gevent, gevent.pool, gevent.event, gevent.queue
import gipc

class Barrier (object) :
    def __init__ (self, count) :
        self.count = self._count = count
        self.event = gevent.event.Event()
    def __str__ (self) :
        return "barrier[%s/%s]" % (self._count - self.count, self._count)
    def wait (self) :
        self.count -= 1
        if self.count :
            self.event.wait()
        else :
            self.event.set()

class call (object) :
    group = gevent.pool.Group()
    def __init__ (self, m, *l, **k) :
        self.m, self.l, self.k = m, l, k
        self.player = self.m.im_self
        self.method = self.m.__name__
        self.group.spawn(self._go)
    def __str__ (self) :
        return "call(%s.%s, *%s, **%s)" % (self.player.name, self.method,
                                           self.l, self.k)
    def _go (self) :
        return self.m(*self.l, **self.k)

join = call.group.join

class ServerPool (object) :
    def __init__ (self, count, **args) :
        self.pids = []
        self._p = [] # processes
        self._r = gevent.queue.Queue() # ready
        self.init(None, args)
        for num in range(count) :
            one, two = gipc.pipe(True)
            proc = gipc.start_process(target=self.remote, args=(one, num, args))
            self.pids.append(proc.pid)
            self._r.put(two)
            self._p.append((proc, two))
    def kill (self) :
        for proc, pipe in self._p :
            try :
                pipe.close()
            except :
                pass
            try :
                proc.terminate()
            except :
                pass
    def getpipe (self) :
        try :
            return self._r.get_nowait()
        except gevent.queue.Empty :
            return self._r.get()
    def putpipe (self, pipe) :
        return self._r.put_nowait(pipe)
    def call (self, *l, **k) :
        pipe = self.getpipe()
        try :
            pipe.put((l, k))
        except gipc.GIPCClosed :
            # end of simulation
            gevent.getcurrent().kill()
        try :
            resp = pipe.get()
        except EOFError :
            # end of simulation
            gevent.getcurrent().kill()
        self.putpipe(pipe)
        if isinstance(resp, Exception) :
            raise resp
        else :
            return resp
    def remote (self, pipe, num, args) :
        self.init(num, args)
        while True :
            try :
                l, k = pipe.get()
            except EOFError :
                break
            try :
                resp = self.proceed(*l, **k)
            except Exception as err :
                resp = err
            pipe.put(resp)
        pipe.close()
    def init (self, num, args) :
        self.num = num
        for name, value in args.items() :
            setattr(self, name, value)
    def proceed (self, *l, **k) :
        pass

if __name__ == "__main__" :
    # print "## callbacks ##############"
    # def f (n) :
    #     print "hello", n
    #     gevent.sleep(1)
    #     print "bye", n
    # call(f, 1).go()
    # join()
    # print "## barrier ##############"
    # def g (n, b) :
    #     print "salut", n
    #     gevent.sleep(1)
    #     b.wait(call(f, n))
    #     print "a+", n
    # b = Barrier(3)
    # for i in range(3) :
    #     call(g, i, b).go()
    # join()
    print "## pools ##############"
    import time, timeit
    class DummyPool (ServerPool) :
        def proceed (self, message) :
            now = time.time()
            timeit.timeit("2**4**4")
            return "%s %s %.2f" % (message, self.num+1, time.time() - now)
    def dummy (pool, msg) :
        print ">", msg
        resp = pool.call(msg)
        print "<", resp
    for i in range(2, 5) :
        print "## size =", i
        now = time.time()
        pool = DummyPool(i)
        for i in range(5) :
            call(dummy, pool, "hello").go()
            call(dummy, pool, "world").go()
        join()
        pool.shutdown()
        print "time elapsed: %.02fs" % (time.time() - now)

import imp, os.path, glob, math
import numpy as np
import networkx as nx

import medusa.log as log

import snakes.plugins
snk = snakes.plugins.load("gv", "snakes.nets", "snk")
from snakes.utils.abcd.main import main as abcd
import algoabcd

def make (path) :
    net = imp.load_source(os.path.splitext(os.path.basename(path))[0], path).net
    log.build("net %s" % net)
    gn = snk.StateGraph(net)
    gn.build()
    log.debug(None, " = %s state(s) in net" % len(gn))
    log.debug(None, "build abcd model")
    algoabcd.net = net
    a = abcd(["--load=let", "--load=gv", "algo2.abcd"])
    for place in a.place() :
        if place.status.name() in ("entry", "exit", "internal") :
            a.remove_place(place.name)
    log.debug(None, "build abcd state space")
    g = snk.StateGraph(a)
    g.build()
    log.debug(None, " = %s state(s)" % len(g))
    G = nx.DiGraph(name=net.name,
                   subnet=net, substates=gn,
                   net=a, states=g)
    for state in g :
        marking = g.net.get_marking()
        submarking = list(marking["trace"])[0].state
        G.add_node(state,
                   control="p0" if "p0" in submarking else "p1",
                   players=list(marking["players"]),
                   marking=submarking,
                   flows=list(marking("flows")))
    for state in g :
        dead = True
        for succ, trans, mode in g.successors() :
            dead = False
            if "flows+" in trans.name :
                tname = "rpc"
            elif "if self.retry" in trans.name :
                tname = "retry"
            elif "and flow" in trans.name :
                tname = "fire"
            else :
                tname = "idle"
            G.add_edge(state, succ,
                       codeblock=tname,
                       player=mode["self"].trans,
                       status=mode["self"].state)
        G.node[state]["dead"] = dead
    return G

def draw (graph, pos=None, prog="neato") :
    if pos is None :
        pos = nx.nx_pydot.pydot_layout(graph, prog=prog)
    shapes = {"o" : set(graph) - {0},
              "h" : {0}}
    for shape, nodes in shapes.items() :
        col = [graph.node[n].get("color", "white") for n in nodes]
        nx.draw(graph, pos,
                nodelist=nodes,
                node_shape=shape,
                node_color=col,
                node_size=600,
        )
    lbl = {}
    for s, t in graph.edges() :
        lbl[s,t] = "%(player)s.%(codeblock)s" % graph.edge[s][t]
    nx.draw_networkx_edge_labels(graph, pos,
                                 edge_labels=lbl,
                                 font_size=10,
                                 label_pos=.6,
    )
    lbl = {n : graph.node[n]["control"] for n in graph}
    nx.draw_networkx_labels(graph, pos,
                            font_size=10,
                            labels=lbl,
                            with_labels=True,
    )
    return pos

def rotate (pos, angle, zero) :
    pos = pos.copy()
    zero = np.array(zero)
    matrix = np.array([[math.cos(angle), -math.sin(angle)],
                       [math.sin(angle), math.cos(angle)]])
    for k, pt in pos.items() :
        pos[k] = tuple(matrix.dot(np.array(pt) - zero))
    return pos

def deadlocks (G) :
    states = G.graph["substates"]
    count = 0
    deadlocks = set()
    for node in G :
        if G.node[node]["dead"] :
            count += 1
            mark = G.node[node]["marking"]
            state = states._state[mark]
            deadlocks.add(mark)
            if list(states.successors(state)) :
                log.error("invalid dealock", node, "=> %s=%s" % (state, mark))
    if count == 0 :
        log.info("no deadlock found")
    else :
        log.info("checked %s deadlock(s)" % count)
    for state in states :
        if not list(states.successors()) :
            mark = states.net.get_marking()
            if mark not in deadlocks :
                log.err("missing deadlock: %s" % mark)
    return count

def m2s (markings) :
    l = []
    for m in markings :
        l.append("{%s}" % ", ".join(str(p) for p in sorted(m)))
    return "{%s}" % ", ".join(sorted(l))

def progress (G) :
    S = nx.DiGraph()
    S.add_edges_from((x,y) for x, y in S.edges()
                     if S.edge[x][y]["codeblock"] != "fire")
    scc = len(list(nx.strongly_connected_components(S)))
    if scc > 0 :
        log.err("found %s SCC without a fire" % scc)
    else :
        log.info("no SCC without a fire")

def remove_dead (G) :
    S = nx.DiGraph()
    S.add_edges_from(G.edges())
    deadlocks = set(n for n in G.node if G.node[n]["dead"])
    done = False
    while not done :
        done = True
        for node in set(S.node) - deadlocks :
            if nx.descendants(S, node).issubset(deadlocks) :
                done = False
                deadlocks.add(node)
    S.remove_nodes_from(deadlocks)
    return S

# def correctness (G) :
#     errors = 0
#     states = G.graph["substates"]
#     for node in G :
#         mark = G.node[node]["marking"]
#         state = states._state[mark]
#         succ1 = (set(states[s] for s, t, m in states.successors(state))
#                  - {mark, snk.Marking()})
#         succ2 = (set(G.node[n]["marking"] for n in nx.descendants(G, node))
#                  - {mark, snk.Marking()})
#         if succ1 != succ2 :
#             errors += 1
#             log.err("successors of %s do not match: %s / %s"
#                     % (node, m2s(succ1), m2s(succ2)))
#     return errors

def tau_star_reduce (G) :
    M = G.copy()
    M.remove_edges_from((s, t, k) for s, t, k in M.edges(keys=True)
                        if k == "*" and s ==t)
    todo = [(s, t, k) for s, t, k in M.edges(keys=True) if k == "*"]
    while todo :
        src, tgt, key = todo.pop()
        if key == "*" :
            M.add_edges_from((s, tgt, k, {})
                             for s in M.predecessors(src)
                             for k in M.edge[s][src].keys()
                             if s != tgt or k != "*")
            M.add_edges_from((tgt, t, k, {})
                             for t in M.successors(src)
                             for k in M.edge[src][t].keys()
                             if t != tgt or k != "*")
            M.remove_node(src)
            todo = [(s, t, k) for s, t, k in M.edges(keys=True) if k == "*" and s != t]
    return M

def lts (G) :
    R = nx.MultiDiGraph()
    for state in G :
        marking = G.net.get_marking()
        if "players" in marking :
            R.add_node(state,
                       init=(state == 0),
                       marking=set(list(marking["trace"])[0].state))
        else :
            R.add_node(state,
                       init=(state == 0),
                       marking=set(marking))
    for state in G :
        for succ, trans, mode in G.successors() :
            if "self" not in mode :
                R.add_edge(state, succ, trans.name)
            elif "and flow" in trans.name :
                R.add_edge(state, succ, mode["self"].trans)
            else :
                R.add_edge(state, succ, "*")
    return R

def ltsdraw (G) :
    pos = nx.nx_pydot.pydot_layout(G, prog="neato")
    nx.draw(G, pos, node_color="white")
    nx.draw_networkx_labels(G, pos, {n : str(n) for n in G.node})
    nx.draw_networkx_edge_labels(G, pos,
                                 {(s,t) : k for s, t, k in G.edges(keys=True)},
                                 label_pos=.6)

def correctness (G) :
    def match (a, b) :
        return a == b
    return nx.is_isomorphic(tau_star_reduce(lts(G.graph["states"])),
                            lts(G.graph["substates"]),
                            node_match=match, edge_match=match)

if __name__ == "__main__" :
    log.verbosity = log.ALL
    for path in glob.glob("nets/*.py") :
        g = make(path)
        d = deadlocks(g)
        progress(g)
        if nx.is_strongly_connected(g) :
            log.info("strongly connected")
        elif d :
            if nx.is_strongly_connected(remove_dead(g)) :
                log.info("strongly connected (except deadlocks)")
            else :
                log.err("not strongly connected (even without deadlocks)")
        else :
            log.err("not strongly connected but without deadlocks")
        if correctness(g) :
            log.info("checked tau*-bisimilarity")
        else :
            log.err("marking graphs are not tau*-bisimilar")
        print

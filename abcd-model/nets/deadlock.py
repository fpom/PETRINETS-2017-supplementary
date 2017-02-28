import snakes.plugins
snk = snakes.plugins.load("gv", "snakes.nets", "snk")
from snk import PetriNet, Place, Transition, Value, dot

net = PetriNet("deadlock")

net.add_place(Place("p0", [dot]))
net.add_place(Place("p1"))

net.add_transition(Transition("t0"))
net.add_transition(Transition("t1"))
net.add_transition(Transition("t2"))

net.add_input("p0", "t1", Value(dot))
net.add_input("p0", "t2", Value(dot))
net.add_input("p1", "t0", Value(dot))

net.add_output("p1", "t1", Value(dot))
net.add_output("p0", "t0", Value(dot))

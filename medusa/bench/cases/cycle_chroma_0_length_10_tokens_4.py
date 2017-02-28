from medusa.bench.models.cycle import Cycle

model = Cycle(chroma=0, length=10, tokens=4)
model.build()
net = model.net

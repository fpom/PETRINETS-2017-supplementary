from medusa.bench.models.hyperloop import HyperLoop

model = HyperLoop(chroma=0, dim=2, width=2)
model.build()
net = model.net

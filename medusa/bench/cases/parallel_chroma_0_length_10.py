from medusa.bench.models.parallel import Parallel

model = Parallel(chroma=0, length=10)
model.build()
net = model.net

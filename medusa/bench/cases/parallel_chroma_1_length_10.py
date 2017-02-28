from medusa.bench.models.parallel import Parallel

model = Parallel(chroma=1, length=10)
model.build()
net = model.net

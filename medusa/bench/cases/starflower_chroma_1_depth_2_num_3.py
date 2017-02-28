from medusa.bench.models.starflower import StarFlower

model = StarFlower(chroma=1, depth=2, num=3)
model.build()
net = model.net

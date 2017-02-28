from medusa.bench.models.starflower import StarFlower

model = StarFlower(chroma=0, depth=2, num=3)
model.build()
net = model.net

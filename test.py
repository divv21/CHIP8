import pyglet

window = pyglet.window.Window(640, 320)
batch = pyglet.graphics.Batch()

# load your pixel.png
pixel = pyglet.resource.image('pixel.png')

# make a grid of 10x10 "pixels"
sprites = []
for y in range(32):
    for x in range(64):
        s = pyglet.sprite.Sprite(pixel, x=x*10, y=310 - y*10, batch=batch)
        s.scale_x = 10 / pixel.width
        s.scale_y = 10 / pixel.height
        sprites.append(s)

@window.event
def on_draw():
    window.clear()
    batch.draw()

pyglet.app.run()

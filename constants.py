import os

# Buttons id
LEFT_CLICK = 1
RIGHT_CLICK = 2

# Hex types
GRASS = 101
WATER = 102
BUILDING = 103
RESOURCE = 104

# Building types
CASTLE = 1031
STORAGE = 1032
ROAD = 1033
CANTEEN = 1034

# Storage types
WOODEN = 81
STONE = 82

# Resources types
FOREST = 1041
MINE = 1042

# Game Actions
BUILD = 20
MAKE_PATH = 21
DESTROY = 22

# Game presets
FPS = 30
RATE = 1 / FPS
STANDARD_WIDTH = 64
STANDARD_HEIGHT = 48
RESOURCES_FOR_BUILD = {STORAGE: (10, 0, 10), ROAD: (0, 5, 3)}
MANS_FOR_DESTROY = {STORAGE: 5, ROAD: 1}
MANS_FOR_ATTACK = {STORAGE: 8}
IMAGES_PATH = "./images"
SPRITES_PATHS = {k: os.path.join(IMAGES_PATH, v) for k, v in
                 {
                     GRASS: "earth/grass.png",
                     WATER: "earth/water.png",
                     CASTLE: "building/castle.png",
                     FOREST: "resource/forest.png",
                     STORAGE: "building/storage.png"
                 }.items()
                 }
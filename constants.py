import os

# Buttons id
LEFT_CLICK = 1
RIGHT_CLICK = 2

# Hex types
GRASS = 101
WATER = 102
BUILDING = 103
RESOURCE = 104
MENU = 105

# Menu background
MENU_BACKGROUND = 1051
DEFAULT_MENU = 1052
BUILD_MENU = 1053
UPGRADE_MENU = 1054
TOP_LINE_MENU = 1055

# Building types
CASTLE = 1031
STORAGE = 1032
ROAD = 1033
CANTEEN = 1034
PROJECT = 1039

# Storage types
WOODEN = 81
STONE = 82

# Resources types
FOREST = 1041
MINE = 1042

# Resource
WOOD = 1043
ROCK = 1044

# Game Actions
BUILD = 20
MAKE_PATH = 21
DELETE_PATH = 22
DESTROY = 23
BACKWARD = 24
# Menu specials
ACCEPT = 25
CANCEL = 26
ASK = 29
# -------------

# GAME MODES
NORMAL = 6
PATH_MAKING = 7

# Game presets
FPS = 30
PADDING = 10
RATE = 1 / FPS
STANDARD_WIDTH = 64
STANDARD_HEIGHT = 48
RESOURCES_FOR_BUILD = {STORAGE: (10, 0, 10), ROAD: (0, 5, 3), CANTEEN: (10, 0, 10)}
MANS_FOR_DESTROY = {STORAGE: 5, ROAD: 1}
MANS_FOR_ATTACK = {STORAGE: 8}
IMAGES_PATH = "./images"
SPRITES_PATHS = {k: os.path.join(IMAGES_PATH, v) for k, v in
                 {
                     GRASS: "earth/grass.png",
                     WATER: "earth/water.png",
                     CASTLE: "building/castle.png",
                     FOREST: "resource/forest.png",
                     STORAGE: "building/storage.png",
                     MENU_BACKGROUND: "menu_icon/menu.png",
                     WOOD: "resource/wood.png",
                     PROJECT: "building/project.png",
                     CANTEEN: "building/canteen.png",
                     DELETE_PATH: "menu_icon/minus.png",
                     MAKE_PATH: "menu_icon/plus.png",
                     DESTROY: "menu_icon/destroy.png",
                     BUILD: "menu_icon/menu_build.png",
                     BACKWARD: "menu_icon/menu_backward.png",
                     ACCEPT: "menu_icon/accept.png",
                     CANCEL: "menu_icon/cancel.png",
                 }.items()
                 }
MENU_PATHS = {k: os.path.join(IMAGES_PATH, v) for k, v in
              {
                  ROAD: "building/road.png",
                  CANTEEN: "building/canteen.png",
                  STORAGE: "building/castle.png",
              }.items()
              }
PLAYER_COLORS = {
    1: (255, 0, 0),
    2: (0, 255, 0),
    3: (0, 0, 255)
}
TRADE = {FOREST: 10,
         MINE: 10}

# Font sizes
STANDARD_FONT = 22
STATUSBAR_FONT = 22

# Hex Tips
tips = {CANTEEN: {"title": "Canteen",
                  "text": "When man run nearby he restore his hungry parameter"}}

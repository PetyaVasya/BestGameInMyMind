import os

# Buttons id
import pygame

LEFT_CLICK = 1
RIGHT_CLICK = 2
STANDARD = 3
# -------------

# Hex types
GRASS = 101
WATER = 102
BUILDING = 103
RESOURCE = 104
MENU = 105
# -------------

# Menu background
MENU_BACKGROUND = 1051
DEFAULT_MENU = 1052
BUILD_MENU = 1053
UPGRADE_MENU = 1054
TOP_LINE_MENU = 1055
# -------------

# Building types
CASTLE = 1031
STORAGE = 1032
ROAD = 1033
CANTEEN = 1034
BARRACKS = 1035
TOWER = 1036
PROJECT = 1039
# -------------

# Storage types
WOODEN = 81
STONE = 82
# -------------

# Resources types
FOREST = 1041
MINE = 1042
# -------------

# Resource
WOOD = 1043
ROCK = 1044
MEN = 1045
# -------------

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
# -------------

# Elements Position
TOP = 810
CENTER = 811
BOTTOM = 812
BETWEEN = 813
LEFT = 814
MIDDLE = 815
RIGHT = 816
TOP_LEFT = 817
TOP_RIGHT = 818
BOTTOM_LEFT = 819
BOTTOM_RIGHT = 820
# -------------

# Orientations
VERTICAL = 10000
HORIZONTAL = 100001
# -------------

# Errors
ERROR = 40000
EMAIL_UNFILLED = 40001
PASSWORD_UNFILLED = 40002
EMAIL_EXIST = 40003
NAME_EXIST = 40004
USER_NOT_EXIST = 40005
WRONG_PASSWORD = 40006
USER_ONLINE = 40007
NOT_AUTHORISED = 40008
STILL_RUNNING = 40009
BAD_EMAIL = 40010
NAME_UNFILLED = 40011
WHAT = 40012
FRIEND_REQUEST_EXIST = 40013
YOU_FRIENDS = 40014
WHO_IS_IT = 40015
USER_OFFLINE = 40016
SESSION_NOT_EXIST = 40017
GAME_IS_FULL = 40018
GAME_STARTED = 40019
GAME_FINISHED = 40020
USER_NOT_IN_GAME = 40021
SERVER_DONT_WORK = 40022
YOU_IN_SESSION = 40023
# -------------

# Status
PENDING = 5551
CONFIRMED = 5552
ONLINE = 2
OFFLINE = 1
# -------------

# Dialog buttons
OK_BUTTON = 12  # 1100
YES_BUTTON = 4  # 100
NO_BUTTON = 2  # 10
CANCEL_BUTTON = 1  # 1
# -------------

# Server constants
S_PENDING = 4
STARTED = 6
FINISHED = 7
# ------------

# Pages
MAIN = 1000000

# -----------

# Specials
GHOST = 77777


class TRANSPARENT:

    def __isub__(self, other):
        return self

    def __add__(self, other):
        return self

    def __iadd__(self, other):
        return self

    def __sub__(self, other):
        return self

    def __mul__(self, other):
        return self

    def __truediv__(self, other):
        return self

    def __floordiv__(self, other):
        return self


# -------------

# Game presets
FPS = 30
PADDING = 10
RATE = 1 / FPS
STANDARD_WIDTH = 64
STANDARD_HEIGHT = 48
START_WOOD = START_ROCKS = 5
RESOURCES_FOR_BUILD = {CANTEEN: (3, 0, 10), BARRACKS: (6, 3, 10), TOWER: (5, 5, 10)}
MANS_FOR_DESTROY = {STORAGE: 5, ROAD: 1}
MANS_FOR_ATTACK = {STORAGE: 8}
ATTACK_RATES = {TOWER: 1, CASTLE: 1}
ATTACK_RANGES = {TOWER: 128, CASTLE: 128}

IMAGES_PATH = "./images"
SPRITES_PATHS = {k: os.path.join(IMAGES_PATH, v) for k, v in
                 {
                     GRASS: "earth/grass.png",
                     WATER: "earth/water.png",
                     CASTLE: "building/castle.png",
                     FOREST: "resource/forest.png",
                     MINE: "resource/mine.png",
                     # STORAGE: "building/storage.png",
                     WOOD: "resource/wood.png",
                     ROCK: "resource/rocks.png",
                     MEN: "resource/men.png",
                     PROJECT: "building/project.png",
                     CANTEEN: "building/canteen.png",
                     BARRACKS: "building/barracks.png",
                     TOWER: "building/tower.png",
                 }.items()
                 }
MENU_PATHS = {k: os.path.join(IMAGES_PATH, v) for k, v in
              {
                  ROAD: "building/road.png",
                  CANTEEN: "menu_icon/canteen.png",
                  STORAGE: "menu_icon/castle.png",
                  BARRACKS: "menu_icon/barracks.png",
                  TOWER: "menu_icon/tower.png",
                  DELETE_PATH: "menu_icon/minus.png",
                  MENU_BACKGROUND: "menu_icon/menu.png",
                  MAKE_PATH: "menu_icon/plus.png",
                  DESTROY: "menu_icon/destroy.png",
                  BUILD: "menu_icon/menu_build.png",
                  BACKWARD: "menu_icon/menu_backward.png",
                  ACCEPT: "menu_icon/accept.png",
                  CANCEL: "menu_icon/cancel.png",
              }.items()
              }
BACKGROUNDS = {k: os.path.join(IMAGES_PATH, v) for k, v in
               {
                   MAIN: "backgrounds/background.jpg",
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
STANDARD_FONT = 16
STATUSBAR_FONT = 22

# Hex Tips
tips = {CANTEEN: {"title": "Столовая Зины",
                  "text": "Когда мужики летят меситься рядом с этой чудной столовой кухарки Зины"
                          " им хватает аромата, чтобы восполнить параметры голода."
                          "\n(3 Полена, 0 Камней, 10 Мужиков)"},
        TOWER: {"title": "Башня Анатолия",
                "text": "Анатолий еще в детстве, живя близ Чернобыля, наблюдал, как за окном ничком"
                        " падают птицы. Мы заметили этот талант, поэтому теперь Анатолий сверлит"
                        " взглядом ваших мужиков, а от проживания в Чернобыле у него осталась лишь"
                        " способность к телепортации."
                        "\n(5 Полен, 5 Камней, 10 Мужиков)"},
        BARRACKS: {"title": "Казармы",
                   "text": "Именно здесь на свет появляются настоящие мужчины"
                           "\n(6 Поленьев, 3 Камня, 10 Мужиков)"},
        DELETE_PATH: {"title": "Ножнички",
                      "text": "Ой-ёй-ёй, каких дорог вы напряли, разобраться в них? Да сам черт"
                              " ногу сломит. Предлагаю все удалить."},
        MAKE_PATH: {"title": "Настройка пути",
                    "text": "Пора проложить путь для ваших верных мужиков, ведь хоть они"
                            " первосортные подхалимы и каблуки, без вашей указки действовать"
                            " они бояться. (Ctrl + Click удалить участок пути)"},
        BUILD: {"title": "Возведение",
                "text": "Вашей империи пора расширяться. Захватите весь мир, выстройте свое имя"
                        " из зданий (в этом, кстати, поможет кнопочка Shift, если у вас"
                        " хватает ресурсов), а если вы промахнулись, то сможете забрать свои"
                        " ресурсы обратно, если мужики не успели добраться и все растащить"
                        " до вас."},
        DESTROY: {"title": "Кто это здесь оставил?",
                  "text": "Кажется, что на вашем поле кто-то творит бесовщину и пора бы это"
                          " исправить? Пару щелчков пальцами и та-дам все исправлено."
                          "Ой, или это были ваши строения?"},
        ROCK: {"title": "Камушки",
               "text": "Помните, эти камни добыты потом и кровью, а не подобраны с римских дорог,"
                       " так что тратьте их аккуратно, если найдете как."},
        WOOD: {"title": "Поленья",
               "text": "А вы думали, что мужики рубят лес? Если бы их кто-то научил, но вам повезло"
                       ", что леса в этом районе волшебные, и бревна катяться прямо в руки"
                       " мужикам, ну или не совсем..."},
        MEN: {"title": "Мужики",
              "text": "Каждому же хотелось посчитать сколько тараканов у него бегает на кухне?"
                      "1, 2, 3... Ладно, ладно, мы уже посчитали."},
        }

# Colors
BASE_COLOR = pygame.Vector3(63, 65, 67)

# Hahahahahahahahahahahahahahahhahahahahahahahahahahahhahaahahahah. Realy?
# SERVER = "https://dag1-flask-app.herokuapp.com/"
# SERVER = "http://127.0.0.1:5000"
# SERVER = "http://5ac15b4c.ngrok.io"
SERVER = "http://69be0ff0.ngrok.io"

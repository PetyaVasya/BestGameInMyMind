import pygame
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from math import cos, sin, radians, ceil
from shapely.geometry import LineString
from Environment import *
from Tools import *
from constants import *
from Settings import SessionAttributes
import json
from UI import *

# from Environment import create_hexagon


'''
Json Map Format:
{
    "session" : hash,
    "hexagons":
        [
            {
                "x": int,
                "y": int,
                "type": "hexagon type",
                *if building*
                "player": ""
                "attributes":
                    {
                
                    } 
            }
        ]
}
'''


class Game:
    hexagons = {}

    def __init__(self, screen):
        self.screen = screen
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.session = None
        self.center = pygame.Vector2(0, 0)

    def init_pygame_variables(self):
        self.center = pygame.Vector2(width / 2 // STANDARD_WIDTH * STANDARD_WIDTH,
                                     height / 2 // STANDARD_HEIGHT * STANDARD_HEIGHT)
        self.hexagons = {GRASS: pygame.transform.scale(pygame.image.load(SPRITES_PATHS[GRASS]),
                                                       (STANDARD_WIDTH, STANDARD_WIDTH)),
                         WATER: pygame.transform.scale(pygame.image.load(SPRITES_PATHS[WATER]),
                                                       (STANDARD_WIDTH, STANDARD_WIDTH)),
                         }

    def flip(self):
        # self.surface.fill((0, 0, 0))
        if self.session:
            self.session.flip()
        self.screen.blit(pygame.transform.scale(self.surface, size), (0, 0))

    def mouse_flip(self, pos):
        if self.session:
            self.session.mouse_flip(pos)

    def tick(self):
        if self.session:
            self.session.tick()

    def buttons_handler(self, events):
        if self.session:
            self.session.increase_shift(-10 * events[pygame.K_a] + 10 * events[pygame.K_d],
                                        -10 * events[pygame.K_w] + 10 * events[pygame.K_s])

    def on_click(self, mouse_pos):
        if self.session:
            self.session.on_click(mouse_pos)

    def create_fight(self, map):
        self.session = Session(self.surface)
        self.session.generate_map(map)

    def get_current_session(self):
        return self.session


class Session:

    def __init__(self, screen):
        self.field = None
        self.screen = screen
        self.attributes = SessionAttributes()
        self.finished = False
        self.shift = pygame.Vector2(0, 0)
        self.selected = None
        self.menu = GameMenu(self.screen, width=width)
        self.menu.set_world_position(0, height - STANDARD_WIDTH * 2.5)
        self.statusbar = Statusbar(self.screen, width=width)
        self.game_mode = NORMAL
        self.statusbar.set_bar("wood", 100000000000000000, pygame.image.load(SPRITES_PATHS[WOOD]))
        self.statusbar.set_bar("wood1", 100000000000000000, pygame.image.load(SPRITES_PATHS[WOOD]))
        self.statusbar.set_bar("wood2", 100000000000000000, pygame.image.load(SPRITES_PATHS[WOOD]))
        self.pseudo_path = None

    def generate_map(self, map):
        self.field = Field(self.screen, map)

    def increase_shift(self, x, y):
        self.shift.x -= x
        self.shift.y -= y

    def get_attributes(self):
        return self.attributes

    def on_click(self, pos):
        if pos.y < 20:
            return
        elif pos.y > (height - STANDARD_WIDTH * 2.5):
            self.menu.on_click(pos)
            return
        clicked_pos = self.field.get_click(pos - self.shift)
        clicked = self.field.get_hexagon(*clicked_pos)
        if self.game_mode == PATH_MAKING and clicked is not self.selected and (
                clicked.type != BUILDING or clicked.player != self.get_player() or clicked.building_type == PROJECT):
            if LineString(list(self.pseudo_path.points) + [clicked_pos]).is_simple:
                self.pseudo_path.add_point(clicked_pos)
            return
        elif self.game_mode == PATH_MAKING:
            return
        if self.menu.action == DESTROY and clicked.type == BUILDING:
            clicked.destroy()
            self.menu.clear()
        elif self.menu.action == BUILD and self.menu.build and clicked.type == GRASS:
            self.field.set_hexagon(self.menu.build, *clicked_pos)
            self.menu.clear()
        elif self.menu.action == MAKE_PATH and clicked.type == BUILDING and (
                UnitSpawn in clicked.__class__.__bases__):
            self.game_mode = PATH_MAKING
            if len(clicked.path) > 1:
                self.pseudo_path = clicked.path.copy()
            else:
                self.pseudo_path = Path(deque([clicked_pos]), player=self.get_player())
            self.selected = clicked
            self.menu.action = ASK
        elif self.menu.action == DELETE_PATH and isinstance(clicked, Path):
            pass
        elif not self.menu.action and clicked.type == BUILDING:
            self.selected = clicked
        elif not self.menu.action:
            self.selected = None

    def make_menu(self, hexagon=None):
        if hexagon:
            pass
        else:
            # Standard Menu
            pass

    def end_path_making(self, result):
        if result:
            self.selected.path = self.pseudo_path.copy()
        else:
            pass
        self.selected = None
        self.game_mode = NORMAL
        self.pseudo_path = None

    def action_handler(self, action, *attrs):
        if action == MAKE_PATH:
            func = self.selected.add_path_point
        func(*attrs)

    def __bool__(self):
        return not self.finished

    def flip(self):
        self.field.flip(self.shift, self.game_mode != PATH_MAKING)
        if self.pseudo_path:
            self.pseudo_path.paint(self.screen, self.shift, True)
        self.menu.flip()
        self.statusbar.flip()

    def mouse_flip(self, pos):
        if (pos.y < 20) or (pos.y > (height - STANDARD_WIDTH * 2.5)):
            # pygame.mouse.set_visible(True)
            return
        elif self.menu.build:
            self.menu.build.set_hexagon(self.field.get_click(pos - self.shift))
            # pygame.mouse.set_visible(False)
            self.menu.build.paint(self.screen, self.shift)

    def tick(self):
        self.field.tick()

    def get_player(self):
        return 1


class Field:

    def __init__(self, screen, map, start=(0, 0)):
        self.start = start
        self.screen = screen
        self.width = STANDARD_WIDTH // 2
        self.height = STANDARD_HEIGHT
        self.map = {}
        self.convert_map(map)
        self.tiles = []

    def tick(self):
        for i in self.map.values():
            i.tick()

    def flip(self, shift=pygame.Vector2(0, 0), show_selected=True):
        # pygame.display.update(self.tiles)
        special = []
        self.tiles = []
        sdv = shift.x // STANDARD_WIDTH, shift.y // STANDARD_HEIGHT
        for i in range(int(get_game().center.x // STANDARD_WIDTH * -2),
                       int(get_game().center.x // STANDARD_WIDTH * 2)):
            current = self.map.get(((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1]), GRASS)
            if current == GRASS:
                current_hexagon = get_game().hexagons[GRASS]
                self.tiles.append(self.screen.blit(current_hexagon,
                                                   (
                                                       get_game().center.x + i * STANDARD_WIDTH +
                                                       shift.x % STANDARD_WIDTH + 32 * (
                                                               sdv[1] % 2),
                                                       get_game().center.y
                                                       + shift.y % STANDARD_HEIGHT)
                                                   )
                                  )
                textsurface = myfont.render(
                    '{}, {}'.format((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1]),
                    False, (0, 0, 0))
                self.screen.blit(textsurface, (
                    get_game().center.x + i * STANDARD_WIDTH + shift.x % STANDARD_WIDTH + 32 * (
                            sdv[1] % 2) + 16, get_game().center.y + shift.y % STANDARD_HEIGHT + 32))
            else:
                special.append((int(UnitSpawn in current.__class__.__bases__), current))
            ma = int(get_game().center.y // STANDARD_WIDTH * 2)
            for j in range(int(get_game().center.y // STANDARD_WIDTH * -2),
                           int(get_game().center.y // STANDARD_WIDTH * 2)):
                if j:
                    current = self.map.get(
                        ((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma, j - sdv[1]), GRASS)
                    if current == GRASS:
                        current_hexagon = get_game().hexagons[GRASS]
                        self.tiles.append(self.screen.blit(current_hexagon,
                                                           (
                                                               get_game().center.x + i * STANDARD_WIDTH + 32 * (
                                                                       abs(j) - abs(sdv[
                                                                                        1]) % ma) + shift.x % STANDARD_WIDTH,
                                                               get_game().center.y + (
                                                                       j * STANDARD_HEIGHT) +
                                                               shift.y % STANDARD_HEIGHT)))
                        textsurface = myfont.render(
                            '{}, {}'.format((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma,
                                            j - sdv[1]),
                            False,
                            (0, 0, 0))
                        self.screen.blit(textsurface,
                                         (get_game().center.x + i * STANDARD_WIDTH + 32 * (
                                                 abs(j) - abs(sdv[1]) % ma) + shift[
                                              0] % STANDARD_WIDTH + 16,
                                          get_game().center.y + (j * STANDARD_HEIGHT) + shift[
                                              1] % STANDARD_HEIGHT + 32))
                    else:
                        special.append((int(UnitSpawn in current.__class__.__bases__), current))
        for i in sorted(special, key=lambda x: x[0]):
            if show_selected and i[1] is get_game().get_current_session().selected:
                i[1].paint(self.screen, shift, True)
            else:
                i[1].paint(self.screen, shift)

    def get_click(self, vector2):
        return get_hexagon_by_world_pos(vector2)

    def get_hexagon(self, x, y):
        return self.map.get((x, y),
                            create_hexagon(get_game().get_current_session().get_player(), (x, y),
                                           GRASS))

    def convert_map(self, map):
        for hexagon in map["hexagons"]:
            hexagon_pos = hexagon["x"], hexagon["y"]
            attrs = hexagon["attributes"]
            if hexagon["type"] == BUILDING:
                hexagon_type = attrs["struct"]
                del attrs["struct"]
            elif hexagon["type"] == RESOURCE:
                hexagon_type = attrs["resource"]
                del attrs["resource"]
            else:
                hexagon_type = hexagon["type"]
            self.map[hexagon_pos] = create_hexagon(
                hexagon["player"],
                hexagon_pos, hexagon_type,
                *(list(attrs.values())[0].values() if hexagon_type == PROJECT else attrs.values()))

    def intersect_hexagon(self, pos, player):
        hexagon = self.get_hexagon(*pos)
        if isinstance(hexagon, Source):
            hexagon.increase(player)
            return True
        elif isinstance(hexagon, Project):
            hexagon = hexagon.intersect(player)
            self.map[pos] = hexagon
            return True
        return False

    def set_hexagon(self, hexagon, *args):
        if len(args) == 1:
            self.map[args[0]] = hexagon
        elif len(args) == 2:
            self.map[args] = hexagon

    # def get_current_hexagon_sprite(data):
    #     if data["type"] == BUILDING:
    #         return data["attributes"]["struct"]


# map = {(3, 3): {"type":
#                 }}
map = json.loads(open("test.json").read())


def get_game():
    return game


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    myfont = pygame.font.SysFont('Comic Sans MS', STANDARD_FONT)
    size = width, height = 800, 600
    screen = pygame.display.set_mode(size)
    game = Game(screen)
    game.init_pygame_variables()
    running = True
    clock = pygame.time.Clock()
    game.create_fight(map)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                game.on_click(pygame.Vector2(event.pos))
                pass
        pressed = pygame.key.get_pressed()
        game.buttons_handler(pressed)
        game.tick()
        game.flip()
        if pygame.mouse.get_focused():
            game.mouse_flip(pygame.Vector2(pygame.mouse.get_pos()))
        pygame.display.flip()
        clock.tick(FPS)
        # size = width, height = pygame.display.get_surface().get_size()

from __future__ import annotations
from collections import deque
from typing import Optional
import pygame
from shapely.geometry import LineString, Point
from shapely.geometry.polygon import Polygon
from Environment import Castle, Canteen, Storage, Project, Source, create_hexagon, UnitSpawn, Path
from constants import *
from Settings import SessionAttributes
from UI import Tip, GameMenu, Statusbar
from math import sin, cos, radians
import ptext

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


class SingletonMeta(type):
    """
    В Python класс Одиночка можно реализовать по-разному. Возможные способы
    включают себя базовый класс, декоратор, метакласс. Мы воспользуемся
    метаклассом, поскольку он лучше всего подходит для этой цели.
    """

    _instance: Optional[Game] = None

    def __call__(self) -> Game:
        if self._instance is None:
            self._instance = super().__call__()
        return self._instance


class Game(metaclass=SingletonMeta):
    hexagons = {}

    def __init__(self):
        self.screen = None
        self.surface = None
        # self.surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        self.session = None
        self.center = pygame.Vector2(0, 0)
        self.tips = {k: Tip(v["title"], v["text"]) for k, v in tips.items()}

    def set_surface(self, screen):
        self.screen = screen
        self.surface = screen

    def init_pygame_variables(self):
        self.center = pygame.Vector2(self.screen.get_width() / 2 // STANDARD_WIDTH * STANDARD_WIDTH,
                                     self.screen.get_height() / 2 // STANDARD_HEIGHT * STANDARD_HEIGHT)
        self.hexagons = {GRASS: pygame.transform.scale(pygame.image.load(SPRITES_PATHS[GRASS]),
                                                       (STANDARD_WIDTH, STANDARD_WIDTH)),
                         WATER: pygame.transform.scale(pygame.image.load(SPRITES_PATHS[WATER]),
                                                       (STANDARD_WIDTH, STANDARD_WIDTH)),
                         }

    def flip(self):
        # self.surface.fill((0, 0, 0))
        if self.session:
            self.session.flip()
        self.screen.blit(pygame.transform.scale(self.surface, self.surface.get_size()), (0, 0))

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


class Session:

    def __init__(self, screen):
        self.field = None
        self.screen = screen
        self.attributes = SessionAttributes()
        self.finished = False
        self.shift = pygame.Vector2(0, 0)
        self.selected = None
        self.menu = GameMenu(self.screen, width=screen.get_width())
        self.menu.set_world_position(0, screen.get_height() - STANDARD_WIDTH * 2.5)
        self.statusbar = Statusbar(self.screen, width=screen.get_width())
        self.game_mode = NORMAL
        self.statusbar.set_bar("wood", 100000000000000000, pygame.image.load(SPRITES_PATHS[WOOD]))
        self.statusbar.set_bar("wood1", 100000000000000000, pygame.image.load(SPRITES_PATHS[WOOD]))
        self.statusbar.set_bar("wood2", 100000000000000000, pygame.image.load(SPRITES_PATHS[WOOD]))
        self.pseudo_path = None
        self.player = 1

    def generate_map(self, map):
        self.field = Field(self.screen, map)

    def increase_shift(self, x, y):
        self.shift.x -= x
        self.shift.y -= y

    def on_click(self, pos):
        if pos.y < 20:
            return
        elif pos.y > (self.screen.get_height() - STANDARD_WIDTH * 2.5):
            self.menu.on_click(pos)
            return
        clicked_pos = self.field.get_click(pos - self.shift)
        clicked = self.field.get_hexagon(*clicked_pos)
        if self.game_mode == PATH_MAKING and clicked is not self.selected and (
                clicked.type != BUILDING or clicked.player != self.player or clicked.building_type == PROJECT):
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
                self.pseudo_path = Path(deque([clicked_pos]), player=self.player)
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
        if pos.y < 20:
            return
        elif pos.y > (self.screen.get_height() - STANDARD_WIDTH * 2.5):
            hovered = Game().tips.get(self.menu.get_hexagon_by_pos(pos))
            if hovered:
                hovered.paint(self.screen, pos)
            return
        elif self.menu.build:
            self.menu.build.set_hexagon(self.field.get_click(pos - self.shift))
            # pygame.mouse.set_visible(False)
            self.menu.build.paint(self.screen, self.shift)

    def tick(self):
        self.field.tick()


class Field:

    def __init__(self, screen, map, start=(0, 0)):
        self.start = start
        self.screen = screen
        self.width = STANDARD_WIDTH // 2
        self.height = STANDARD_HEIGHT
        self.map = {}
        self.convert_map(map)
        self.tiles = []
        self.myfont = pygame.font.SysFont('Comic Sans MS', STANDARD_FONT)

    def tick(self):
        for i in self.map.values():
            i.tick()

    def flip(self, shift=pygame.Vector2(0, 0), show_selected=True):
        # pygame.display.update(self.tiles)
        special = []
        self.tiles = []
        sdv = shift.x // STANDARD_WIDTH, shift.y // STANDARD_HEIGHT
        game = Game()
        for i in range(int(game.center.x // STANDARD_WIDTH * -2),
                       int(game.center.x // STANDARD_WIDTH * 2)):
            current = self.map.get(((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1]), GRASS)
            if current == GRASS:
                current_hexagon = game.hexagons[GRASS]
                self.tiles.append(self.screen.blit(current_hexagon,
                                                   (
                                                       game.center.x + i * STANDARD_WIDTH +
                                                       shift.x % STANDARD_WIDTH + 32 * (
                                                               sdv[1] % 2),
                                                       game.center.y
                                                       + shift.y % STANDARD_HEIGHT)
                                                   )
                                  )
                textsurface = self.myfont.render(
                    '{}, {}'.format((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1]),
                    False, (0, 0, 0))
                self.screen.blit(textsurface, (
                    game.center.x + i * STANDARD_WIDTH + shift.x % STANDARD_WIDTH + 32 * (
                            sdv[1] % 2) + 16, game.center.y + shift.y % STANDARD_HEIGHT + 32))
            else:
                special.append((int(UnitSpawn in current.__class__.__bases__), current))
            ma = int(game.center.y // STANDARD_WIDTH * 2)
            for j in range(int(game.center.y // STANDARD_WIDTH * -2),
                           int(game.center.y // STANDARD_WIDTH * 2)):
                if j:
                    current = self.map.get(
                        ((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma, j - sdv[1]), GRASS)
                    if current == GRASS:
                        current_hexagon = game.hexagons[GRASS]
                        self.tiles.append(self.screen.blit(current_hexagon,
                                                           (
                                                               game.center.x + i * STANDARD_WIDTH + 32 * (
                                                                       abs(j) - abs(sdv[
                                                                                        1]) % ma) + shift.x % STANDARD_WIDTH,
                                                               game.center.y + (
                                                                       j * STANDARD_HEIGHT) +
                                                               shift.y % STANDARD_HEIGHT)))
                        textsurface = self.myfont.render(
                            '{}, {}'.format((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma,
                                            j - sdv[1]),
                            False,
                            (0, 0, 0))
                        self.screen.blit(textsurface,
                                         (game.center.x + i * STANDARD_WIDTH + 32 * (
                                                 abs(j) - abs(sdv[1]) % ma) + shift[
                                              0] % STANDARD_WIDTH + 16,
                                          game.center.y + (j * STANDARD_HEIGHT) + shift[
                                              1] % STANDARD_HEIGHT + 32))
                    else:
                        special.append((int(UnitSpawn in current.__class__.__bases__), current))
        for i in sorted(special, key=lambda x: x[0]):
            if show_selected and i[1] is game.session.selected:
                i[1].paint(self.screen, shift, True)
            else:
                i[1].paint(self.screen, shift)

    def get_click(self, vector2):
        return get_hexagon_by_world_pos(vector2)

    def get_hexagon(self, x, y):
        return self.map.get((x, y),
                            create_hexagon(Game().session.player, (x, y),
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


class Presets:

    def __init__(self):
        pass


class ScreensSystem:

    def __init__(self, surface):
        self.main_surface = surface
        self.screens = {}
        self.current = None

    def add_screen(self, name, screen):
        self.screens[name] = screen
        return self

    def flip(self):
        if self.current:
            self.screens[self.current].flip()
            self.main_surface.blit(self.screens[self.current].surface, (0, 0))

    def get_click(self, pos):
        return self.screens[self.current].get_click(pos)


class Screen:

    def __init__(self, size):
        self.elements = []
        self.surface = pygame.Surface(size)

    def change_size(self, size):
        self.surface = pygame.Surface(size)
        for i in self.elements:
            i[0].screen = self.surface
        return self

    def add_object(self, pos, element):
        self.elements.append((element, pos))
        element.set_world_position(pos)
        element.screen = self.surface
        return self

    def remove_object(self, element):
        for i in range(len(self.elements)):
            if self.elements[i][0] == element:
                self.elements.pop(i)
        return self

    def get_click(self, vector2):
        for i in self.elements:
            if i[0].screen.get_rect().collidepoint(vector2):
                return i[0].get_click(vector2)

    def flip(self):
        for i in self.elements:
            if isinstance(i[0], pygame.sprite.Sprite) or isinstance(i[0], pygame.Rect) or isinstance(i[0], pygame.Surface):
                self.surface.blit(*i)
            else:
                i[0].flip()

# Screen(size).add_object(size * [0.6, 0.3], ptext.getsurf("Одиночная игра"))\
#     .add_object(size * [0.6, 0.4], ptext.getsurf("Многопользовательская игра"))\
#     .add_object(size * [0.6, 0.5], ptext.getsurf("Настройки"))\
#     .add_object(size * [0.6, 0.6], ptext.getsurf("Выход"))


def get_hexagon_by_world_pos(vector2):
    vector2 = pygame.Vector2(vector2) - Game().center
    current = [int(vector2.x // 32),
               int(vector2.y // STANDARD_HEIGHT)]
    current = current[0] - ((current[0] % 2) ^ (current[1] % 2)), current[1]
    point = Point(vector2.x, vector2.y)
    polygon = Polygon(
        [(current[0] * 32 + round(sin(radians(i))) * 32 + 32,
          current[1] * STANDARD_HEIGHT + round(cos(radians(i)) * 32) + 32) for i in
         range(0, 360, 60)])
    if polygon.contains(point):
        return current[0], current[1]
    else:
        if (vector2.x % 64) > 32:
            return current[0] - 1, current[1] - 1
        else:
            return current[0] + 1, current[1] - 1


def get_hexagon_pos(x, y, shift):
    return pygame.Vector2(x * STANDARD_WIDTH // 2 + STANDARD_WIDTH // 2,
                          y * STANDARD_HEIGHT + STANDARD_WIDTH // 2) + shift + Game().center

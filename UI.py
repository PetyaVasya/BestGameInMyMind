from math import sin, radians, cos

import pygame
import __main__
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import Environment
from constants import *


class UIObject:

    def __init__(self, pos=pygame.Vector2(0, 0)):
        self.world_position = pos

    def set_world_position(self, x, y):
        self.world_position = pygame.Vector2(x, y)

    def set_world_position_vector(self, pos):
        self.world_position = pos

    def upgrade_coords(self, *args):
        return self.world_position + (args[0] if len(args) == 1 else args)


'''
Menu Format
(0, 0) | (2, 0) | (4, 0) | (6, 0)
    (1, 1) | (3, 1) | (5, 1)
(0, 2) | (2, 2) | (4, 2) | (6, 2)
'''


class GameMenu(UIObject):
    menus = {DEFAULT_MENU: {(0, 2): BUILD},
             BUILD: {(2, 2): CANTEEN, (4, 2): ROAD, (1, 1): STORAGE},
             TOP_LINE_MENU: {(0, 0): MAKE_PATH, (2, 0): DELETE_PATH, (4, 0): DESTROY}}

    def __init__(self, screen, pos=pygame.Vector2(0, 0), width=800, height=3):
        super().__init__(pos)
        self.screen = screen
        self.selected = None
        self.action = None
        self.build = None
        self.width = width
        self.height = STANDARD_WIDTH * (height - 0.5)
        self.hexagons = {i: pygame.transform.scale(
            pygame.image.load(SPRITES_PATHS[i]),
            (STANDARD_WIDTH, STANDARD_WIDTH)) for i in
            (MENU_BACKGROUND, DESTROY, DELETE_PATH, MAKE_PATH, BACKWARD, BUILD)
        }
        self.hexagons.update({
            i: pygame.transform.scale(
                pygame.image.load(MENU_PATHS[i]),
                (STANDARD_WIDTH, STANDARD_WIDTH)) for i in
            (CANTEEN, ROAD, STORAGE)
        })

    def flip(self, menu_type=None):
        max_right = self.width // 64
        r_shift = (self.width - max_right * 64) / 2
        for i in range(-1, max_right + 2):
            for j in range(-1, 4):
                rect = [0, 0, STANDARD_WIDTH, STANDARD_WIDTH]
                if (i == -1) and (j % 2):
                    rect[0] = STANDARD_WIDTH - r_shift
                elif i == -1:
                    rect[0] = r_shift
                elif (i == (max_right + 1)) and (j % 2):
                    rect[2] = r_shift
                elif i == (max_right + 1):
                    rect[2] = STANDARD_WIDTH - r_shift
                if j == -1:
                    rect[1] = STANDARD_HEIGHT
                elif j == 3:
                    rect[3] = STANDARD_HEIGHT // 3
                if (self.action and self.action not in self.menus[TOP_LINE_MENU].values()) and (
                        (i * 2 - (j % 2), j) == (0, 2)):
                    current = BACKWARD
                else:
                    current = self.menus.get(self.action, self.menus[DEFAULT_MENU]).get(
                        (i * 2 - (j % 2), j),
                        self.menus[TOP_LINE_MENU].get(
                            (i * 2 - (j % 2), j) if self.action != ASK else MENU_BACKGROUND,
                            MENU_BACKGROUND))
                self.screen.blit(self.hexagons[current],
                                 self.upgrade_coords(
                                     STANDARD_WIDTH * max(0, i) + r_shift * bool(i + 1) - (
                                             STANDARD_WIDTH / 2) * abs(
                                         j % 2), STANDARD_HEIGHT * max(0, j)), rect)
        pygame.draw.line(self.screen, (120, 60, 0), self.upgrade_coords(0, 0),
                         self.upgrade_coords(self.width, 0), width=5)

    def get_click(self, vector2):
        vector2 = pygame.Vector2(vector2)
        r_shift = (self.width - self.width // 64 * 64) / 2
        vector2 -= self.world_position + [-r_shift + STANDARD_WIDTH // 2,
                                          STANDARD_WIDTH // 2 - STANDARD_HEIGHT // 2 + 2.5]
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
                return current[0], current[1]
            else:
                return current[0], current[1]

    def on_click(self, vector2):
        current = self.get_click(vector2)
        action = self.menus[TOP_LINE_MENU].get(current, None)
        if action:
            self.action = action
            self.build = None
        if self.action and (current == (0, 2)):
            self.clear()
        elif self.action == BUILD:
            build = self.menus[BUILD].get(current, None)
            if build:
                self.build = Environment.create_hexagon(__main__.get_game().session.get_player(),
                                                        current, PROJECT, build)
        elif self.menus[DEFAULT_MENU].get(current, None) == BUILD:
            self.action = BUILD
            build = self.menus[BUILD].get(current, None)
            if build:
                self.build = Environment.create_hexagon(__main__.get_game().session.get_player(),
                                                        current, PROJECT, build)
        else:
            self.action = self.menus[DEFAULT_MENU].get(current, None)

    def clear(self):
        self.action = None
        self.build = None


class Statusbar(dict, UIObject):

    def __init__(self, screen, pos=pygame.Vector2(0, 0), base_color=pygame.Vector3(63, 65, 67),
                 width=800, height=20):
        dict.__init__(self)
        UIObject.__init__(self, pos)
        self.screen = screen
        self.base = base_color
        self.height = height
        self.font = pygame.font.SysFont('Comic Sans MS', STATUSBAR_FONT)
        self.width = width

    def __setitem__(self, key, value):
        if not value.priority:
            priorities = set(range(1, len(self) + 1))
            value.priority = next(iter(priorities - {i.priority for i in self.values()}), 1)
            value.icon = pygame.transform(value.icon, (self.height * 0.8, self.height * 0.8))
        if not isinstance(value, Bar):
            raise TypeError("Only Bar's objects can be add")
        super().__setitem__(key, value)

    def get_min_priority(self):
        priorities = set(range(1, len(self) + 1))
        return next(iter(priorities - {i.priority for i in self.values()}), 1)

    def set_bar(self, name, value, icon=None, priority=0):
        if icon:
            icon = pygame.transform.scale(icon, (int(self.height * 0.8), int(self.height * 0.8)))
        bar = Bar(value, icon, priority if priority else self.get_min_priority())
        super().__setitem__(name, bar)

    def strip_value(self, value, max_size):
        max_size -= self.height * 0.8 + 2 * PADDING
        if isinstance(value, str):
            if max_size < self.font.size(value)[0]:
                value = value[:-3]
                while max_size < self.font.size(value + "...")[0]:
                    value = value[:-1]
                value += "..."
        elif isinstance(value, int):
            max_v = "9" * int(max_size // self.font.size("9")[0] - 2)
            if int(max_v) < value:
                value = max_v + "+"
            else:
                value = str(value)
        return value

    def flip(self):
        center = self.height * 0.45
        # max_width = width // 5
        pygame.draw.line(self.screen, self.base, self.upgrade_coords(0, center),
                         self.upgrade_coords(self.width, center), self.height)
        section = min(self.width // len(self.values()), self.width // 5)
        bar_color = self.base * 0.75
        for ind, bar in enumerate(sorted(self.values(), key=lambda x: x.priority)):
            pygame.draw.line(self.screen, bar_color,
                             self.upgrade_coords(ind * section + PADDING, center),
                             self.upgrade_coords(ind * section + section - PADDING, center),
                             self.height - 4)
            if bar.icon:
                self.screen.blit(bar.icon,
                                 self.upgrade_coords(ind * section + PADDING, self.height * 0.2))
            self.screen.blit(
                self.font.render(self.strip_value(bar.value, section), False, (240, 240, 240)),
                self.upgrade_coords(ind * section + PADDING + self.height * 0.8, self.height * 0.2))


class Bar:

    def __init__(self, value, icon=None, priority=0):
        self.icon = icon
        self.value = value
        self.priority = priority


class ProgressBar(UIObject):

    def __init__(self, maximum, pos=pygame.Vector2(0, 0), base_color=pygame.Vector3(63, 65, 67),
                 width=STANDARD_WIDTH, height=16):
        super().__init__(pos)
        self.maximum = maximum
        self.value = 0
        self.width = width
        self.height = height
        self.color = base_color

    def set_value(self, value):
        self.value = min(0, max(self.maximum, value))

    def set_maximum(self, maximum):
        self.maximum = maximum

    def __iadd__(self, other):
        if isinstance(other, int):
            self.value = min(self.maximum, self.value + other)
            return self
        else:
            raise TypeError("Add only int")

    def __isub__(self, other):
        if isinstance(other, int):
            self.value = max(0, self.value - other)
            return self
        else:
            raise TypeError("Sub only int")

    def flip(self, surface, shift):
        center = self.height // 2
        for i in range(1, 3):
            val = 0
            if (i == 2) and self.value:
                pygame.draw.circle(surface, (0, 0, 255),
                                   self.upgrade_coords(center, center + 1) + shift, center // i)
                val = (self.width - self.height) * (self.value / self.maximum)
                pygame.draw.line(surface, (0, 0, 255),
                                 self.upgrade_coords(center, center) + shift,
                                 self.upgrade_coords(center + val, center) + shift,
                                 self.height // i)
            else:
                pygame.draw.circle(surface, self.color // i,
                                   self.upgrade_coords(center, center + 1) + shift, center // i)
            pygame.draw.line(surface, self.color // i,
                             self.upgrade_coords(val + center, center) + shift,
                             self.upgrade_coords(self.width - center, center) + shift,
                             self.height // i)
            if (i == 2) and (self.value == self.maximum):
                pygame.draw.circle(surface, (0, 0, 255),
                                   self.upgrade_coords(self.width - center, center + 1) + shift,
                                   center // i)
            else:
                pygame.draw.circle(surface, self.color // i,
                                   self.upgrade_coords(self.width - center, center + 1) + shift,
                                   center // i)

    def is_full(self):
        return self.value == self.maximum

    def is_empty(self):
        return self.value == 0

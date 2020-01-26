from math import sin, radians, cos

import pygame
import __main__
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

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

    def __init__(self, screen, pos=pygame.Vector2(0, 0), width=800, height=3):
        super().__init__(pos)
        self.screen = screen
        self.selected = None
        self.action = None
        self.width = width
        self.height = STANDARD_WIDTH * (height - 0.5)
        self.background = pygame.transform.scale(
            pygame.image.load(SPRITES_PATHS[MENU_BACKGROUND]),
            (STANDARD_WIDTH, STANDARD_WIDTH))

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
                self.screen.blit(self.background, self.upgrade_coords(
                    STANDARD_WIDTH * max(0, i) + r_shift * bool(i + 1) - (STANDARD_WIDTH / 2) * abs(
                        j % 2), STANDARD_HEIGHT * max(0, j)), rect)
        pygame.draw.line(self.screen, (120, 60, 0), self.upgrade_coords(0, 0),
                         self.upgrade_coords(self.width, 0), width=5)

    def get_click(self, vector2):
        vector2 = pygame.Vector2(vector2)
        r_shift = (self.width - self.width // 64 * 64) / 2
        vector2 -= self.world_position + [-r_shift + STANDARD_WIDTH // 2,
                                          STANDARD_WIDTH // 2 - STANDARD_HEIGHT // 2 + 2.5]
        print(vector2)
        current = [int(vector2.x // 32),
                   int(vector2.y // STANDARD_HEIGHT)]
        current = current[0] - ((current[0] % 2) ^ (current[1] % 2)), current[1]
        point = Point(vector2.x, vector2.y)
        polygon = Polygon(
            [(current[0] * 32 + round(sin(radians(i))) * 32 + 32,
              current[1] * STANDARD_HEIGHT + round(cos(radians(i)) * 32) + 32) for i in
             range(0, 360, 60)])
        if polygon.contains(point):
            print("contains")
            return current[0], current[1]
        else:
            if (vector2.x % 64) > 32:
                return current[0], current[1]
            else:
                return current[0], current[1]


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

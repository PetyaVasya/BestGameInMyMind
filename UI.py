from math import sin, radians, cos, ceil, floor
from copy import copy

import pygame
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

import Environment
from constants import *
from decorators import *
import ptext
import Game


class UIObject:

    def __init__(self, pos=pygame.Vector2(0, 0), width=0, height=0):
        self.world_position = pos
        self.rect = pygame.Rect(*pos, width, height)

    @update_pos
    def set_world_position(self, pos):
        self.world_position = pos
        self.rect.x = pos.x
        self.rect.y = pos.y
        return self

    def upgrade_coords(self, *args):
        return self.world_position + (args[0] if len(args) == 1 else args)

    def set_size(self, width, height):
        self.rect = pygame.Rect(0, 0, width, height)

    def get_click(self, pos: pygame.Vector2):
        pass

    def mouse_flip(self, pos: pygame.Vector2):
        pass

    def check_pressed(self, pressed):
        pass

    def mouse_up(self):
        pass

    def tick(self, delta):
        pass


class Drawable:

    @check_transparent
    def draw_rect(self, color, rect, width=None, surface=None):
        if width:
            return pygame.draw.rect((surface if surface else self.screen), color, rect, width)
        return pygame.draw.rect((surface if surface else self.screen), color, rect)

    @check_transparent
    def draw_circle(self, color, center, radius, width=None, surface=None):
        if width:
            return pygame.draw.circle((surface if surface else self.screen), color, center, radius,
                                      width)
        return pygame.draw.circle((surface if surface else self.screen), color, center, radius)

    @check_transparent
    def draw_polygon(self, color, points, width=None, surface=None):
        if width:
            return pygame.draw.polygon((surface if surface else self.screen), color, points,
                                       width)
        return pygame.draw.polygon((surface if surface else self.screen), color, points)


'''
Menu Format
(0, 0) | (2, 0) | (4, 0) | (6, 0)
    (1, 1) | (3, 1) | (5, 1)
(0, 2) | (2, 2) | (4, 2) | (6, 2)
'''


class GameMenu(UIObject):
    menus = {DEFAULT_MENU: {(0, 2): BUILD},
             BUILD: {(2, 2): CANTEEN, (4, 2): ROAD, (1, 1): STORAGE},
             TOP_LINE_MENU: {(0, 0): MAKE_PATH, (2, 0): DELETE_PATH, (4, 0): DESTROY},
             ASK: {(0, 2): ACCEPT, (2, 2): CANCEL}}

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
            (MENU_BACKGROUND, DESTROY, DELETE_PATH, MAKE_PATH, BACKWARD, BUILD, ACCEPT, CANCEL)
        }
        self.hexagons.update({
            i: pygame.transform.scale(
                pygame.image.load(MENU_PATHS[i]),
                (STANDARD_WIDTH, STANDARD_WIDTH)) for i in
            (CANTEEN, ROAD, STORAGE)
        })

    def flip(self, menu_type=None):
        # print(self.action)
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

                if self.action not in self.menus[TOP_LINE_MENU].values() and (
                        (i * 2 - (j % 2), j) == (0, 2)) and self.action and self.action != ASK:
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

    def get_hexagon_by_pos(self, pos):
        click_hex = self.get_click(pos)
        return self.menus.get(self.action, self.menus[TOP_LINE_MENU]).get(click_hex, self.menus[
            DEFAULT_MENU].get(click_hex, None))

    def on_click(self, vector2):
        current = self.get_click(vector2)
        action = self.menus[TOP_LINE_MENU].get(current, None)
        if action:
            self.action = action
            self.build = None
            return
        action = self.menus[ASK].get(current, None)
        game = Game.Game()
        if self.action == ASK and action:
            game.session.end_path_making(action == ACCEPT)
            self.action = None
        elif self.action and (current == (0, 2)):
            self.clear()
        elif self.action == BUILD:
            build = self.menus[BUILD].get(current, None)
            if build:
                self.build = Environment.create_hexagon(game.session.player,
                                                        current, PROJECT, build)
        elif self.menus[DEFAULT_MENU].get(current, None) == BUILD:
            self.action = BUILD
            build = self.menus[BUILD].get(current, None)
            if build:
                self.build = Environment.create_hexagon(game.session.player,
                                                        current, PROJECT, build)
        else:
            self.action = self.menus[DEFAULT_MENU].get(current, None)

    def clear(self):
        self.action = None
        self.build = None


class Statusbar(dict, UIObject):

    def __init__(self, screen, pos=pygame.Vector2(0, 0), base_color=BASE_COLOR,
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


class ProgressBar(UIObject, Drawable):

    def __init__(self, maximum, pos=pygame.Vector2(0, 0), base_color=BASE_COLOR,
                 width=STANDARD_WIDTH, height=16, vertical=False, rounded=True, t_float=False):
        super().__init__(pos, width, height)
        self.maximum = maximum
        self.value = 0
        if vertical:
            self.bar_rect = pygame.Rect(width // 4, width // 4, width // 2, height - width // 4)
        else:
            self.bar_rect = pygame.Rect(height // 4, height // 4, height // 2, width - height // 4)
        self.bar_rect = self.bar_rect.move(*self.world_position)
        self.color = base_color
        self.vertical = vertical
        self.rounded = rounded
        self.t_float = t_float

    def set_value(self, value):
        self.value = min(0, max(self.maximum, value))

    def set_maximum(self, maximum):
        self.maximum = maximum

    def __iadd__(self, other):
        if isinstance(other, int) or self.t_float:
            self.value = min(self.maximum, self.value + other)
            return self
        else:
            raise TypeError("Add only int")

    def __isub__(self, other):
        if isinstance(other, int) or self.t_float:
            self.value = max(0, self.value - other)
            return self
        else:
            raise TypeError("Sub only int")

    def __add__(self, other):
        if isinstance(other, int) or self.t_float:
            self.value = min(self.maximum, self.value + other)
            return self
        else:
            raise TypeError("Add only int")

    def __sub__(self, other):
        if isinstance(other, int) or self.t_float:
            self.value = max(0, self.value - other)
            return self
        else:
            raise TypeError("Sub only int")

    def flip(self, surface, shift, as_text=False):
        if as_text:
            print(self.upgrade_coords(shift))
            surface.blit(
                ptext.getsurf("{}/{}".format(self.value, self.maximum)), self.upgrade_coords(shift))
            return
        center = self.rect.w // 2 if self.vertical else self.rect.h // 2
        p = (self.rect.w if self.vertical else self.rect.h)
        np = (self.rect.w if not self.vertical else self.rect.h)
        for i in range(1, 3):
            val = 0
            if (i == 2) and self.value:
                new = pygame.Vector2(center, center + self.vertical ^ 1)
                pygame.draw.circle(surface, (0, 0, 255),
                                   self.upgrade_coords(new.yx if self.vertical else new.xy + shift),
                                   center // i)
                val = ((self.rect.h - self.rect.w) if self.vertical else (
                        self.rect.w - self.rect.h)) \
                      * (self.value / self.maximum)
                new = pygame.Vector2(center, center - self.vertical)
                new1 = pygame.Vector2(center + val, center - self.vertical)
                pygame.draw.line(surface, (0, 0, 255),
                                 self.upgrade_coords(new.yx if self.vertical else new.xy + shift),
                                 self.upgrade_coords(new1.yx if self.vertical else new1.xy + shift),
                                 p // i)
            else:
                if self.rounded:
                    new = pygame.Vector2(center, center + self.vertical ^ 1)
                    pygame.draw.circle(surface, self.color,
                                       self.upgrade_coords(
                                           new.yx if self.vertical else new.xy + shift), center)
                else:
                    pygame.draw.rect(surface, self.color,
                                     list(self.upgrade_coords(shift)) + [p, p])
            new = pygame.Vector2(val + center, center - self.vertical)
            new1 = pygame.Vector2(np - center, center - self.vertical)
            pygame.draw.line(surface, self.color // i,
                             self.upgrade_coords(new.yx if self.vertical else new.xy + shift),
                             self.upgrade_coords(new1.yx if self.vertical else new1.xy + shift),
                             p // i)
            if (i == 2) and (self.value == self.maximum):
                new = pygame.Vector2(np - center, center + self.vertical ^ 1)
                pygame.draw.circle(surface, (0, 0, 255),
                                   self.upgrade_coords(new.yx if self.vertical else new.xy + shift),
                                   center // i)
            else:
                if self.rounded or i == 2:
                    new = pygame.Vector2(np - center, center + self.vertical ^ 1)
                    pygame.draw.circle(surface, self.color // i,
                                       self.upgrade_coords(
                                           new.yx if self.vertical else new.xy + shift),
                                       center // i)
                elif i == 1:
                    new = pygame.Vector2(np - p, 0)
                    pygame.draw.rect(surface, self.color,
                                     list(self.upgrade_coords(
                                         new.yx if self.vertical else new.xy + shift)) + [p, p])

    def is_full(self):
        return self.value == self.maximum

    def is_empty(self):
        return self.value == 0


class Tip:

    def __init__(self, title="", text="", width=300, background=(0, 0, 0),
                 border_color=(255, 0, 0)):
        self.title = title
        self.text = text
        self.width = width
        self.background_color = background
        self.border_color = border_color
        self.border_width = 3
        self.title_surf = ptext.getsurf(title, width=width, bold=True, underline=True)
        self.text_surf = ptext.getsurf(text, width=width)
        self.height = self.title_surf.get_height() + self.text_surf.get_height()

    def set_data(self, title, text):
        # game = Game.Game()
        self.title_surf = ptext.getsurf(title, width=self.width, bold=True, underline=True)
        self.text_surf = ptext.getsurf(text, width=self.width)
        self.height = self.title_surf.get_height() + self.text_surf.get_height()

    def text_to_size(self, width, height):
        pass

    def paint(self, screen, pos):
        paint_pos = pygame.Vector2(pos)
        if pos.y + self.height + 2 * self.border_width > screen.get_height():
            paint_pos.y -= self.height + 2 * self.border_width
        if pos.x + self.width + 2 * self.border_width > screen.get_width():
            paint_pos.y -= self.width + 2 * self.border_width
        pygame.draw.rect(screen, self.background_color,
                         [paint_pos.x + self.border_width - 1, paint_pos.y + self.border_width - 1,
                          self.width + 2,
                          self.height + 2])
        pygame.draw.rect(screen, self.border_color,
                         [paint_pos.x, paint_pos.y, self.width + 2 * self.border_width,
                          self.height + 2 * self.border_width], self.border_width)
        screen.blit(self.title_surf, paint_pos + [self.border_width] * 2)
        screen.blit(self.text_surf, paint_pos + [self.border_width,
                                                 self.border_width + self.title_surf.get_height()])


class Button(UIObject):

    def __init__(self, screen, pos=pygame.Vector2(0, 0)):
        super().__init__(pos)
        self.screen = screen
        self.background = None
        self.action = None
        self.rect = pygame.Rect(*pos, 0, 0)

    def set_background(self, surface):
        self.background = surface
        self.rect = pygame.Rect(*self.world_position, *surface.get_size())
        return self

    def set_action(self, action):
        self.action = action
        return self

    @click_in
    @zero_args
    def get_click(self):
        return self.action()

    @zero_args
    def flip(self):
        self.screen.blit(self.background, self.world_position)


class ScrollBar(ProgressBar):
    def __init__(self, maximum, pos=pygame.Vector2(0, 0), base_color=BASE_COLOR,
                 width=STANDARD_WIDTH, height=16, rounded=True):
        super().__init__(maximum, pos, base_color, width, height, vertical=True, rounded=rounded,
                         t_float=True)
        self.moving = False
        self.start = 0
        self.step = (self.rect.h - self.rect.w) / self.maximum
        self.length = max(self.maximum // 5, 1)

    @in_this
    def get_click(self, pos):
        if not self.bar_rect.collidepoint(*pos):
            return None
        self.moving = True
        self.start = (pos.y - self.rect.w // 2) / self.step
        if self.value <= self.start <= (self.value + self.length):
            pass
            # print("123")
            # self.start = self.value - self.length // 2
            # self.value = self.start
            return 0
        elif self.start > self.value:
            s = self.value
            self.value = max(0, min(self.value + 1, self.maximum - self.length))
            self.moving = False
            return self.value - s
        else:
            s = self.value
            self.value = max(0, min(self.value - 1, self.maximum - self.length))
            self.moving = False
            return self.value - s

    def set_size(self, width, height):
        self.rect.w = width
        self.rect.h = height
        self.step = (self.rect.h - self.rect.w) / self.maximum
        self.bar_rect = pygame.Rect(width // 4, width // 4, width // 2, height - width // 4)

    def set_maximum(self, maximum):
        super().set_maximum(maximum)
        self.length = max(self.maximum // 5, 1)
        self.step = (self.rect.h - self.rect.w) / self.maximum

    @in_this
    def mouse_flip(self, pos):
        if not self.rect.collidepoint(*pos):
            self.moving = False
            return None
        if self.moving:
            current = (pos.y - self.rect.w // 2) / self.step
            delta = min(0.99, max(-0.99, current - self.start))
            self.start = max(0, min(self.maximum, self.start + delta))
            s = self.value % 1
            self.value = max(0, min(self.value + delta, self.maximum - self.length))
            return s + delta
        else:
            return 0

    def mouse_up(self):
        self.moving = False

    def flip(self, surface, shift=pygame.Vector2()):
        super().flip(surface, shift)
        center = self.rect.w // 2
        pygame.draw.circle(surface, (self.color // 2 if self.value else (0, 0, 255)),
                           self.upgrade_coords(center, center) + shift, center // 2)
        if self.value:
            pygame.draw.line(surface, self.color // 2,
                             self.upgrade_coords(center - 1, center) + shift,
                             self.upgrade_coords(center - 1,
                                                 center + self.step * self.value) + shift,
                             center)
        pygame.draw.line(surface, (0, 0, 255),
                         self.upgrade_coords(center - 1, center + self.step * max(0, min(self.value,
                                                                                  self.maximum - self.length))) + shift,
                         self.upgrade_coords(center - 1,
                                             center + self.step * min(self.value + self.length,
                                                                      self.maximum)) + shift,
                         center)
        if (self.value + self.length) == self.maximum:
            pygame.draw.circle(surface, (0, 0, 255),
                               self.upgrade_coords(center, self.rect.h - center) + shift,
                               center // 2)


class DataElement(UIObject):

    def __init__(self, screen=None, pos=pygame.Vector2()):
        super().__init__(pos)
        self.view_data = {}
        self.screen = screen
        self.background = None
        self.view = None
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.action = None
        self.data = None

    def set_background(self, surface):
        self.background = surface
        self.rect = pygame.Rect(0, 0, *surface.get_size())
        return self

    def set_action(self, action):
        self.action = action
        return self

    def add_attr(self, k, v):
        locals()[k] = v

    @click_in
    @zero_args
    def get_click(self):
        if self.action:
            return self.action()
        return None

    def tick(self, delta):
        self.view = self.background.copy()
        for i in self.data.keys():
            self.view_data[i](self.view, getattr(self, i))

    def flip(self):
        self.screen.blit(self.view, self.world_position)

    def set_data(self, data):
        """
        Словарь, где ключи - это названия алгоритмов размещения, а значения - переменные,
         которые в них передаются
        :param data:
        :return:
        """
        if self.data:
            for i in self.data.keys():
                delattr(self, i)
        self.data = data
        for k, v in data.items():
            setattr(self, k, v)
        print(data)
        self.tick(0)
        return self

    def copy(self):
        new = DataElement(self.screen, self.world_position).set_background(
            self.background).set_action(self.action)
        new.view_data = self.view_data
        return new


class DataRecycleView(UIObject):

    def __init__(self, screen, width, height, pos=pygame.Vector2(),
                 base_color=BASE_COLOR, border=5):
        super().__init__(pos, width, height)
        self.screen = screen
        self.color = base_color
        self.border = border
        print(self.world_position)
        self.data_rect = pygame.Rect(*self.world_position + [self.border, self.border], (width - self.border * 2) * 0.9,
                                     height - self.border * 2)
        self.scroll = ScrollBar(1, pygame.Vector2((width - self.border * 2) * 0.9 + self.border,
                                                  self.border) + self.world_position,
                                width=(width - self.border * 2) * 0.1,
                                height=height - self.border * 2, rounded=False)
        self.elements = []
        self.add_element = None
        self.view = None
        self.count = 0
        self.data = []
        self.app = 0

    def set_view(self, view: DataElement):
        self.view = view
        a = self.data_rect.height / self.view.rect.height
        self.app = a % 1
        self.count = floor(a)
        self.scroll.length = a
        self.elements = [view.copy() for _ in range(self.count + 2)]
        return self

    def set_data(self, data):
        self.data = data
        if not self.count:
            raise Exception("Set View early")
        for i in range(min(len(self.data), self.count + 2)):
            self.elements[i].set_data(self.data[i])
        self.scroll.set_maximum(len(self.data))
        self.scroll.length = self.data_rect.height / self.view.rect.height
        return self

    @in_this
    def get_click(self, pos: pygame.Vector2):
        if self.data_rect.collidepoint(*pos):
            for element in self.elements:
                element.get_click(pos)
        else:
            res = self.scroll.get_click(pos)
            if not res:
                return
            if res > 0:
                if (1 - self.app) < self.scroll.value < len(self.data) - self.count:
                    element = self.elements.pop(0)
                    self.elements.append(element.set_data(self.data[floor(self.scroll.value) + 2]))
            elif res < 0:
                if self.app < self.scroll.value < len(self.data) - self.count - 1:
                    element = self.elements.pop()
                    self.elements.insert(0,
                                         element.set_data(self.data[floor(self.scroll.value) - 1]))

    @in_this
    def mouse_flip(self, pos: pygame.Vector2):
        res = self.scroll.mouse_flip(pos)
        if not res:
            return
        if res > 0:
            a = (self.scroll.value - 1) < (1 - self.app)
            f = floor(res)
            if self.scroll.value < len(self.data) - self.count:
                self.elements = self.elements[max(0, f - a):] + [
                    self.elements[f - i].set_data(
                        self.data[floor(self.scroll.value) + self.count - i + 1])
                    for i in range(f - a, 0, -1)]
        elif res < 0:
            a = self.scroll.value - res > (len(self.data) - 1 + self.app) or self.scroll.value < (
                    1 - self.app)
            f = floor(abs(res)) - 1
            if 1 < self.scroll.value < len(self.data) - self.count - 1:
                self.elements = [
                                    self.elements[i].set_data(
                                        self.data[floor(self.scroll.value) + i]) for i in
                                    range(floor(res) + a, 0)] + self.elements[
                                                                :self.count + 2 + f + a]

    def mouse_up(self):
        self.scroll.mouse_up()

    def flip(self):
        pygame.draw.rect(self.screen, self.color, self.rect)
        pygame.draw.rect(self.screen, self.color // 2, self.data_rect)
        if self.scroll.value < 1 - self.app:
            plus = (1 - self.scroll.value) * self.view.rect.h
            self.screen.blit(self.elements[0].view, self.upgrade_coords(self.border, self.border),
                             pygame.Rect(0, self.view.rect.h - plus, self.view.rect.w, plus))
            ost = self.data_rect.h - plus - (self.count - 1) * self.view.rect.h
            for i in range(1, min(self.count + bool(ost), len(self.data))):
                if i == self.count:
                    self.screen.blit(self.elements[i].view, self.upgrade_coords(self.border,
                                                                                self.border + plus + self.view.rect.h * (
                                                                                        i - 1)),
                                     pygame.Rect(0, 0, self.view.rect.w, ost))
                    continue
                self.screen.blit(self.elements[i].view, self.upgrade_coords(self.border,
                                                                            self.border + plus + self.view.rect.h * (
                                                                                    i - 1)))
        elif self.scroll.value == (len(self.data) - 1):
            self.screen.blit(self.elements[-1].view, (self.border, self.border))
        elif self.scroll.value >= (len(self.data) - self.count + self.app):
            plus = (1 - self.scroll.value % 1) * self.view.rect.h
            self.screen.blit(self.elements[2].view, (self.border, self.border),
                             pygame.Rect(0, self.view.rect.h - plus, self.view.rect.w, plus))
            ost = self.data_rect.h - plus
            for i in range(3, self.count + 1 + bool(ost)):
                if i == self.count + 1:
                    self.screen.blit(self.elements[i].view,
                                     self.upgrade_coords(self.border,
                                                         self.border + plus + self.view.rect.h * (
                                                                 i - 3)),
                                     pygame.Rect(0, 0, self.view.rect.w, ost))
                    continue
                self.screen.blit(self.elements[i].view,
                                 self.upgrade_coords(self.border,
                                                     self.border + plus + self.view.rect.h * (
                                                             i - 3)))
        else:
            plus = (1 - self.scroll.value % 1) * self.view.rect.h
            self.screen.blit(self.elements[1].view, self.upgrade_coords(self.border, self.border),
                             pygame.Rect(0, self.view.rect.h - plus, self.view.rect.w, plus))
            ost = self.data_rect.h - plus - (self.count - 1) * self.view.rect.h
            for i in range(2, self.count + 1 + bool(ost)):
                if i == self.count + 1:
                    self.screen.blit(self.elements[i].view,
                                     self.upgrade_coords(self.border,
                                                         self.border + plus + self.view.rect.h * (
                                                                 i - 2)),
                                     pygame.Rect(0, 0, self.view.rect.w, ost))
                    continue
                self.screen.blit(self.elements[i].view,
                                 self.upgrade_coords(self.border,
                                                     self.border + plus + self.view.rect.h * (
                                                             i - 2)))
        self.scroll.flip(self.screen, pygame.Vector2())


class DataLayout(UIObject, Drawable):

    def __init__(self, screen, width, height, pos=pygame.Vector2(),
                 base_color=BASE_COLOR, border=5, v_align=TOP, h_align=LEFT, orientation=VERTICAL):
        super().__init__(pos, width, height)
        self.screen = screen
        self.color = base_color
        self.border = border
        self.data_rect = pygame.Rect(self.border, self.border, width - self.border * 2,
                                     height - self.border * 2).move(*self.world_position)
        self.elements = []
        self.v_align = v_align
        self.h_align = h_align
        self.orientation = orientation

    def add_element(self, element):
        self.elements.append(element)
        element.screen = self.screen
        self.move_elements()

    def remove_element(self, element):
        self.elements.remove(element)
        self.move_elements()

    def pop_element(self, element):
        a = self.elements.pop(element)
        self.move_elements()
        return a

    def move_elements(self):
        if self.orientation == VERTICAL:
            el_h = self.data_rect.h - sum(map(lambda x: x.rect.h, self.elements))
            n = 0
            if self.v_align == CENTER:
                el_h //= 2
            elif self.v_align == TOP:
                el_h = 0
            elif self.v_align == BETWEEN:
                n = el_h // (len(self.elements) + 1)
                el_h = n
            for e in self.elements:
                e.set_world_position(pygame.Vector2(self.border + (
                    (self.data_rect.w - e.rect.w) if self.h_align == RIGHT else (
                        ((self.data_rect.w - e.rect.w) // 2) if self.h_align == MIDDLE else 0)),
                                                  self.border + el_h) + self.world_position)
                el_h += e.rect.h + n
        else:
            el_w = self.data_rect.w - sum(map(lambda x: x.rect.w, self.elements))
            n = 0
            if self.h_align == MIDDLE:
                el_w //= 2
            elif self.h_align == LEFT:
                el_w = 0
            elif self.h_align == BETWEEN:
                n = el_w // (len(self.elements) + 1)
                el_w = n
            for e in self.elements:
                e.set_world_position(pygame.Vector2(self.border + el_w, self.border + (
                    (self.data_rect.h - e.rect.h) if self.h_align == BOTTOM else (((
                                                                                               self.data_rect.h - e.rect.h) // 2) if self.h_align == CENTER else 0))) + self.world_position)
                el_w += e.rect.w + n

    @click_in
    def get_click(self, pos: pygame.Vector2):
        for el in self.elements:
            r = el.get_click(pos)
            if r:
                return r

    @zero_args
    def flip(self):
        self.draw_rect(self.color, self.rect)
        self.draw_rect(self.color // 2, self.data_rect)
        for e in self.elements:
            e.flip(self.screen, pygame.Vector2())


class Toast(UIObject, Drawable):

    def __init__(self, screen, text, time=1000, title=None, pos=pygame.Vector2(), width=0, height=0,
                 border=5, align=None):
        super().__init__(pos, width, height)
        self.screen = screen
        self.align = align
        if self.align == CENTER:
            self.set_world_position(
                pygame.Vector2(self.screen.get_rect().center) - pygame.Vector2(self.rect.left))
        elif self.align == TOP_LEFT:
            self.set_world_position(self.screen.get_rect().topleft)
        elif self.align == TOP_RIGHT:
            self.set_world_position(pygame.Vector2(self.screen.get_rect().topright) - [width, 0])
        elif self.align == BOTTOM_LEFT:
            self.set_world_position(pygame.Vector2(self.screen.get_rect().bottomleft) - [0, height])
        elif self.align == BOTTOM_RIGHT:
            self.set_world_position(
                pygame.Vector2(self.screen.get_rect().bottomright) - [width, height])
        elif self.align == LEFT:
            self.set_world_position(self.screen.get_rect().left,
                                    self.screen.get_rect().centery - self.rect.centery)
        elif self.align == RIGHT:
            self.set_world_position(self.screen.get_rect().right - width,
                                    self.screen.get_rect().centery - self.rect.centery)
        elif self.align == BOTTOM:
            self.set_world_position(self.screen.get_rect().centerx - self.rect.left,
                                    self.screen.get_rect().bottom - height)
        elif self.align == TOP:
            self.set_world_position(self.screen.get_rect().centerx - self.rect.left,
                                    self.screen.get_rect().top)
        self.color = BASE_COLOR
        self.border = border
        self.headline_rect = pygame.Rect(self.border, 0, width - self.border * 2,
                                         height * 0.2).move(*self.world_position)
        if title:
            self.title = ptext.getsurf(title, width=self.headline_rect.w, align="center")
        else:
            self.title = None
        self.inner_rect = pygame.Rect(self.border, height * 0.2, width - self.border * 2,
                                      height * 0.8 - self.border).move(*self.world_position)
        self.text = ptext.getsurf(text, width=self.inner_rect.w, align="center")
        self.time = time
        self.alive = True

    def tick(self, delta):
        self.time -= delta
        if self.time > 0:
            return True
        else:
            self.alive = False
            return False

    @on_alive
    @zero_args
    def flip(self):
        self.draw_rect(self.color, self.rect)
        self.draw_rect(self.color // 2, self.inner_rect)

        if self.title:
            self.screen.blit(self.title, self.headline_rect.move(
                (self.headline_rect.w - self.title.get_width()) // 2,
                (self.headline_rect.h - self.title.get_height()) // 2))
        else:
            self.draw_rect(self.color // 2, self.headline_rect.move(0, self.border))
        self.screen.blit(self.text,
                         self.inner_rect.move((self.inner_rect.w - self.text.get_width()) // 2,
                                              (self.inner_rect.h - self.text.get_height()) // 2))


class Dialog(Toast):

    def __init__(self, screen, text, buttons=12, title=None, pos=pygame.Vector2(), width=0,
                 height=0,
                 border=5, align=None):
        super().__init__(screen, text, time=0, title=title, pos=pos, width=width, height=height,
                         border=border, align=align)
        self.color = BASE_COLOR
        self.buttons = DataLayout(screen, self.inner_rect.w, self.inner_rect.h * 0.1,
                                  pygame.Vector2(self.border,
                                                 self.border + self.inner_rect.h * 0.9) + self.world_position,
                                  base_color=TRANSPARENT(), v_align=CENTER, h_align=BETWEEN,
                                  orientation=HORIZONTAL)
        self.res = None
        btns = {12: "OK", 4: "Yes", 2: "No", 1: "Cancel"}
        for i in (12, 4, 2, 1):
            if buttons >= i:
                buttons -= i
                c = i
                self.buttons.add_element(
                    Button(screen).set_action(lambda: self.close(c)).set_background(
                        ptext.getsurf(btns[i])))

    @click_in
    def get_click(self, pos: pygame.Vector2):
        return self.buttons.get_click(pos)

    def close(self, btn):
        self.res = btn
        self.alive = False

    def tick(self, delta):
        if not self.alive:
            return self.res
        else:
            return None

    @on_alive
    @zero_args
    def flip(self):
        super().flip()
        self.buttons.flip()


class Image(UIObject, Drawable):

    def __init__(self, screen: pygame.Surface, img: pygame.Surface, pos=pygame.Vector2(), border=0, border_color=BASE_COLOR):
        super().__init__(pos, img.get_width() + border * 2, img.get_height() + border * 2)
        self.screen = screen
        self.img = img
        self.border = border
        self.border_color = border_color

    @zero_args
    def flip(self):
        self.draw_rect(self.border_color, self.rect)
        self.screen.blit(self.img, self.rect.move(self.border, self.border))

import pygame
from constants import TRANSPARENT


def zero_args(func):

    def new(self, *args, **kwargs):
        return func(self)

    return new


def update_pos(func):

    def new(self, pos, *args, **kwargs):
        if not isinstance(pos, pygame.Vector2):
            if isinstance(pos, list) or isinstance(pos, tuple):
                pos = pygame.Vector2(pos)
                return func(self, pos, *args, **kwargs)
            else:
                pos = pygame.Vector2(pos, args[0])
                return func(self, pos, *args[1:], **kwargs)
        else:
            return func(self, pos, *args, **kwargs)

    return new


def in_this(func):

    def new(self, pos):
        return func(self, pos - self.world_position)

    return new


def old_click_in(func):

    def new(self, pos):
        if self.rect.move(self.world_position).collidepoint(pos):
            return func(self, pos)
        else:
            return None

    return new


def click_in(func, as_atr=False):

    def new(self, pos):
        if self.rect.collidepoint(pos):
            return func(self, pos, *([True] if as_atr else []))
        elif as_atr:
            return func(self, pos, False)
        else:
            return None

    return new


def check_transparent(func):

    def new(self, color, *args, **kwargs):
        if isinstance(color, TRANSPARENT):
            return
        else:
            return func(self, color, *args, **kwargs)

    return new


def on_alive(func):

    def new(self, *args, **kwargs):
        if self.alive:
            return func(self, *args, **kwargs)
        return None

    return new

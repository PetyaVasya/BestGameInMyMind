from math import radians, sin, cos

import pygame
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from constants import *
import __main__


def get_hexagon_by_world_pos(vector2):
    vector2 = pygame.Vector2(vector2) - __main__.get_game().center
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
                          y * STANDARD_HEIGHT + STANDARD_WIDTH // 2) + shift + __main__.get_game().center


def load_image(name, colorkey=None):
    return pygame.transform.scale(pygame.image.load(name).convert_alpha(),
                                  (STANDARD_WIDTH, STANDARD_WIDTH))

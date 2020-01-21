from math import radians, sin, cos

import pygame
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from constants import *
import __main__


def get_hexagon_by_world_pos(vector2):
    current = [int((vector2.x - __main__.get_game().center_x) // 32),
               int((vector2.y - __main__.get_game().center_y) // STANDARD_HEIGHT)]
    current = current[0] - ((current[0] % 2) ^ (current[1] % 2)), current[1]
    point = Point(vector2.x - __main__.get_game().center_x,
                  vector2.y - __main__.get_game().center_y)
    polygon = Polygon(
        [(current[0] * 32 + round(sin(radians(i))) * 32 + 32,
          current[1] * STANDARD_HEIGHT + round(cos(radians(i)) * 32) + 32) for i in
         range(0, 360, 60)])
    if polygon.contains(point):
        return current[0], current[1]
    else:
        if ((vector2.x - __main__.get_game().center_x) % 64) > 32:
            return current[0] - 1, current[1] - 1
        else:
            return current[0] + 1, current[1] - 1


def load_image(name, colorkey=None):
    return pygame.transform.scale(pygame.image.load(name).convert_alpha(),
                                  (STANDARD_WIDTH, STANDARD_WIDTH))

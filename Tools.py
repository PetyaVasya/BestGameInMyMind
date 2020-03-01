from math import radians, sin, cos

import pygame
# from shapely.geometry import Point
# from shapely.geometry.polygon import Polygon
from constants import *
# from Game import Game


def load_image(name, colorkey=None):
    return pygame.transform.scale(pygame.image.load(name).convert_alpha(),
                                  (STANDARD_WIDTH, STANDARD_WIDTH))

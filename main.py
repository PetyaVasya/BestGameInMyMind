import pygame
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from math import cos, sin, radians, ceil

BASE_R = 64


class Game:

    def __init__(self, screen):
        self.screen = screen
        self.field_surface = pygame.Surface((width, height))
        self.field = Field(self.field_surface)
        self.shift = 0

    def flip(self):
        self.shift += 1
        self.field.flip((self.shift, 0))
        self.screen.blit(pygame.transform.scale(self.field_surface, size), (0, 0))

    def get_click(self, mouse_pos):
        res = self.field.get_click(mouse_pos[0] - self.shift, mouse_pos[1])
        pygame.draw.circle(self.field_surface, (0, 0, 0), (
        res[0] * 64 + 32 * ((res[1] % 2) == 0), res[1] * 48), 2)
        return res


class Field:

    def __init__(self, screen, start=(0, 0)):
        self.start = start
        self.hexagons = {"grass": pygame.transform.scale(pygame.image.load("grass.png"), (64, 64)),
                         }
        self.screen = screen
        self.width = BASE_R // 2
        self.height = 48
        self.center = (width / 2 - self.width) // 64 * 64, (height / 2 - self.width) // 64 * 64
        self.tiles = []

    def flip(self, shift=(0, 0)):
        pygame.display.update(self.tiles)
        self.tiles = []
        for i in range(int((self.center[0] - width / 4 * 3) // self.width),
                       int((self.center[0] + width / 4 * 3) // self.width)):
            screen.blit(self.hexagons["grass"],
                        (i * 64 + shift[0] % 64, self.center[1] + shift[1] % 64))
            self.tiles.append((i * 64 + shift[0] % 64, self.center[1] + shift[1] % 64, 64, 64))
            for j in range(int((self.center[1] - height / 4 * 3) // self.width),
                           int((self.center[1] + height / 4 * 3) // self.width)):
                if j:
                    screen.blit(self.hexagons["grass"],
                                (i * 64 + 32 * abs(j) + shift[0] % 64,
                                 self.center[1] + (j * 48) + shift[1] % 64))
                    self.tiles.append((i * 64 + 32 * abs(j) + shift[0] % 64,
                                       self.center[1] + (j * 48) + shift[1] % 64, 64, 64))

    def get_click(self, x, y):
        x += 32 * ((y // self.height) % 2)
        current = x // 64, y // self.height
        if not x % 64:
            return
        point = Point(x - 32 * ((y // self.height) % 2), y)
        polygon = Polygon(
            [(current[0] * 64 + 32 * (((y // self.height) % 2) == 0) + round(sin(radians(i))) * 32,
              current[1] * self.height + round(cos(radians(i)) * 32)) for i in
             range(0, 360, 60)])
        # print(current)
        # print(x % 64, y % self.height)
        if polygon.contains(point):
            return current[0], current[1]
        else:
            cond = (x % 64) > 32
            # print(current[0] + (1 if cond else - 1) * ((current[1] % 2) ^ cond), current[1] + 1)
            return current[0] + (1 if cond else - 1) * ((current[1] % 2) ^ cond), current[1] + 1


if __name__ == "__main__":
    pygame.init()
    size = width, height = 800, 600
    screen = pygame.display.set_mode(size)
    game = Game(screen)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                res = game.get_click(event.pos)
                # print(event.pos)
                print(res)
        game.flip()
        pygame.display.flip()
        # size = width, height = pygame.display.get_surface().get_size()

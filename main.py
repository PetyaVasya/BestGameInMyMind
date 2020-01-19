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
        self.shift = [0, 0]

    def flip(self):
        self.field.flip(self.shift)
        self.screen.blit(pygame.transform.scale(self.field_surface, size), (0, 0))

    def get_click(self, mouse_pos):
        res = self.field.get_click(mouse_pos[0] - self.shift[0], mouse_pos[1] - self.shift[1])
        # pygame.draw.circle(self.field_surface, (0, 0, 0), (
        # res[0] * 64 + 32 * ((res[1] % 2) == 0), res[1] * 48), 2)
        return res

    def increase_shift(self, x, y):
        self.shift = self.shift[0] - x, self.shift[1] - y


class Field:

    def __init__(self, screen, start=(0, 0)):
        self.start = start
        self.hexagons = {"grass": pygame.transform.scale(pygame.image.load("grass.png"), (64, 64)),
                         "water": pygame.transform.scale(pygame.image.load("water.png"), (64, 64)),
                         "castle": pygame.transform.scale(pygame.image.load("castle.png"),
                                                          (64, 64)),
                         }
        self.screen = screen
        self.width = BASE_R // 2
        self.height = 48
        self.center = width / 2 // 64 * 64, height / 2 // 48 * 48
        self.tiles = []

    def flip(self, shift=(0, 0)):
        pygame.display.update(self.tiles)
        self.tiles = []
        sdv = shift[0] // 64, shift[1] // 48
        for i in range(int(self.center[0] // 64 * -2),
                       int(self.center[0] // 64 * 2)):
            current_hexagon = self.hexagons[
                map.get(((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1]), "grass")]
            screen.blit(current_hexagon,
                        (self.center[0] + i * 64 + shift[0] % 64 + 32 * (sdv[1] % 2),
                         self.center[1] + shift[1] % 48))
            self.tiles.append(
                (self.center[0] + i * 64 + shift[0] % 64, self.center[1] + shift[1] % 48, 64, 64))
            textsurface = myfont.render('{}, {}'.format((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1]),
                                        False, (0, 0, 0))
            screen.blit(textsurface,
                        (self.center[0] + i * 64 + shift[0] % 64 + 32 * (sdv[1] % 2) + 16,
                         self.center[1] + shift[1] % 48 + 32))
            ma = int(self.center[1] // 64 * 2)
            for j in range(int(self.center[1] // 64 * -2),
                           int(self.center[1] // 64 * 2)):
                if j:
                    current_hexagon = self.hexagons[
                        map.get(((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma, j - sdv[1]),
                                "grass")]
                    screen.blit(current_hexagon,
                                (self.center[0] + i * 64 + 32 * (abs(j) - abs(sdv[1]) % ma) + shift[
                                    0] % 64,
                                 self.center[1] + (j * 48) + shift[1] % 48))
                    textsurface = myfont.render(
                        '{}, {}'.format((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma, j - sdv[1]),
                        False,
                        (0, 0, 0))
                    screen.blit(textsurface,
                                (self.center[0] + i * 64 + 32 * (abs(j) - abs(sdv[1]) % ma) + shift[
                                    0] % 64 + 16,
                                 self.center[1] + (j * 48) + shift[1] % 48 + 32))
                    self.tiles.append((self.center[0] + i * 64 + 32 * abs(j) + shift[0] % 64,
                                       self.center[1] + (j * 48) + shift[1] % 48, 64, 64))

    def get_click(self, x, y):
        x -= self.center[0]
        y -= self.center[1]
        current = [int(x // 32), int(y // self.height)]
        current = current[0] - ((current[0] % 2) ^ (current[1] % 2)), current[1]
        # if not x % 64:
        #     return
        point = Point(x, y)
        polygon = Polygon(
            [(current[0] * 32 + round(sin(radians(i))) * 32 + 32,
              current[1] * self.height + round(cos(radians(i)) * 32) + 32) for i in
             range(0, 360, 60)])
        # print(current)
        # print(polygon, x, y)
        # print(x % 64, y % self.height)
        if polygon.contains(point):
            return current[0], current[1]
        else:
            if (x % 64) > 32:
                return current[0] - 1, current[1] - 1
            else:
                return current[0] + 1, current[1] - 1
        # if polygon.contains(point):
        #     return current[0] - self.center[0] // 64, current[1] - self.center[1] // 48
        # else:
        #     cond = (x % 64) > 32
        #     # print(current[0] + (1 if cond else - 1) * ((current[1] % 2) ^ cond), current[1] + 1)
        #     return current[0] + (1 if cond else - 1) * (bool(current[1] % 2) ^ cond) - self.center[0] // 64, current[1] + 1 - self.center[1] // 48


map = {(3, 3): "castle"}

if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    myfont = pygame.font.SysFont('Comic Sans MS', 22)
    size = width, height = 800, 600
    screen = pygame.display.set_mode(size)
    game = Game(screen)
    running = True
    clock = pygame.time.Clock()
    while running:
        # screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                res = game.get_click(event.pos)
                # print(event.pos)
                print(res)
        pressed = pygame.key.get_pressed()
        game.increase_shift(-10 * pressed[pygame.K_a] + 10 * pressed[pygame.K_d],
                            -10 * pressed[pygame.K_w] + 10 * pressed[pygame.K_s])
        game.flip()
        pygame.display.flip()

        clock.tick(30)
        # size = width, height = pygame.display.get_surface().get_size()

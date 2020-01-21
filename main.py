import pygame
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from math import cos, sin, radians, ceil

from Environment import create_hexagon
from Tools import *
from constants import *
from Settings import SessionAttributes
import json

# from Environment import create_hexagon


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


class Game:
    center_x = 0
    center_y = 0
    hexagons = {}

    def __init__(self, screen):
        self.screen = screen
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.current_fight = None

    def init_pygame_variables(self):
        self.center_x = width / 2 // STANDARD_WIDTH * STANDARD_WIDTH
        self.center_y = height / 2 // STANDARD_HEIGHT * STANDARD_HEIGHT
        self.hexagons = {GRASS: pygame.transform.scale(pygame.image.load(SPRITES_PATHS[GRASS]),
                                                       (STANDARD_WIDTH, STANDARD_WIDTH)),
                         WATER: pygame.transform.scale(pygame.image.load(SPRITES_PATHS[WATER]),
                                                       (STANDARD_WIDTH, STANDARD_WIDTH)),
                         }

    def flip(self):
        # self.surface.fill((0, 0, 0))
        if self.current_fight:
            self.current_fight.flip()
            self.screen.blit(pygame.transform.scale(self.surface, size), (0, 0))

    def tick(self):
        if self.current_fight:
            self.current_fight.tick()

    def buttons_handler(self, events):
        if self.current_fight:
            self.current_fight.increase_shift(-10 * events[pygame.K_a] + 10 * events[pygame.K_d],
                                              -10 * events[pygame.K_w] + 10 * events[pygame.K_s])

    def on_click(self, mouse_pos):
        if self.current_fight:
            self.current_fight.on_click(mouse_pos)

    def create_fight(self, map):
        self.current_fight = Fight(self.surface)
        self.current_fight.generate_map(map)

    def get_current_fight(self):
        return self.current_fight


class Fight:

    def __init__(self, screen):
        self.field = None
        self.screen = screen
        self.attributes = SessionAttributes()
        self.finished = False
        self.shift = pygame.Vector2(0, 0)
        self.selected = None
        self.action = MAKE_PATH

    def generate_map(self, map):
        self.field = Field(self.screen, map)

    def increase_shift(self, x, y):
        self.shift.x -= x
        self.shift.y -= y

    def get_attributes(self):
        return self.attributes

    def on_click(self, pos):
        # if pos[1] < 600:
        #     pass
        clicked_pos = self.field.get_click(pos - self.shift)
        clicked = self.field.get_hexagon(*clicked_pos)
        if (clicked == GRASS) and self.action:
            if self.action != DESTROY:
                self.action_handler(self.action, clicked_pos)
            else:
                self.selected = None
                self.action = None
                self.make_menu()
        elif clicked == GRASS:
            self.selected = None
            self.make_menu()
        elif self.selected:
            if self.action == MAKE_PATH:
                self.action_handler(self.action, clicked_pos)
        else:
            self.selected = clicked
            self.make_menu(clicked)

    def make_menu(self, hexagon=None):
        if hexagon:
            pass
        else:
            # Standard Menu
            pass

    def action_handler(self, action, *attrs):
        if action == MAKE_PATH:
            func = self.selected.add_path_point
        func(*attrs)

    def __bool__(self):
        return not self.finished

    def flip(self):
        self.field.flip(self.shift)

    def tick(self):
        self.field.tick()

    def get_player(self):
        return 1


class Field:

    def __init__(self, screen, map, start=(0, 0)):
        self.start = start
        self.screen = screen
        self.width = STANDARD_WIDTH // 2
        self.height = STANDARD_HEIGHT
        self.map = {}
        self.convert_map(map)
        self.tiles = []

    def tick(self):
        for i in self.map.values():
            i.tick()

    def flip(self, shift=pygame.Vector2(0, 0)):
        # pygame.display.update(self.tiles)
        special = []
        self.tiles = []
        sdv = shift.x // STANDARD_WIDTH, shift.y // STANDARD_HEIGHT
        for i in range(int(get_game().center_x // STANDARD_WIDTH * -2),
                       int(get_game().center_x // STANDARD_WIDTH * 2)):
            current = self.map.get(((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1]), GRASS)
            if current == GRASS:
                current_hexagon = get_game().hexagons[GRASS]
                self.tiles.append(self.screen.blit(current_hexagon,
                                                   (
                                                       get_game().center_x + i * STANDARD_WIDTH + shift.x % STANDARD_WIDTH + 32 * (
                                                               sdv[1] % 2),
                                                       get_game().center_y + shift.y % STANDARD_HEIGHT)))
                textsurface = myfont.render(
                    '{}, {}'.format((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1]),
                    False, (0, 0, 0))
                self.screen.blit(textsurface,
                                 (
                                     get_game().center_x + i * STANDARD_WIDTH + shift.x % STANDARD_WIDTH + 32 * (
                                             sdv[1] % 2) + 16,
                                     get_game().center_y + shift.y % STANDARD_HEIGHT + 32))
            else:
                special.append(current)
            ma = int(get_game().center_y // STANDARD_WIDTH * 2)
            for j in range(int(get_game().center_y // STANDARD_WIDTH * -2),
                           int(get_game().center_y // STANDARD_WIDTH * 2)):
                if j:
                    current = self.map.get(
                        ((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma, j - sdv[1]), GRASS)
                    if current == GRASS:
                        current_hexagon = get_game().hexagons[GRASS]
                        self.tiles.append(self.screen.blit(current_hexagon,
                                                           (
                                                           get_game().center_x + i * STANDARD_WIDTH + 32 * (
                                                                   abs(j) - abs(sdv[
                                                                                    1]) % ma) + shift.x % STANDARD_WIDTH,
                                                           get_game().center_y + (
                                                                       j * STANDARD_HEIGHT) +
                                                           shift.y % STANDARD_HEIGHT)))
                        textsurface = myfont.render(
                            '{}, {}'.format((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma,
                                            j - sdv[1]),
                            False,
                            (0, 0, 0))
                        self.screen.blit(textsurface,
                                         (get_game().center_x + i * STANDARD_WIDTH + 32 * (
                                                 abs(j) - abs(sdv[1]) % ma) + shift[
                                              0] % STANDARD_WIDTH + 16,
                                          get_game().center_y + (j * STANDARD_HEIGHT) + shift[
                                              1] % STANDARD_HEIGHT + 32))
                    else:
                        special.append(current)
        for i in special:
            i.paint(self.screen, shift)

    def get_click(self, vector2):
        return get_hexagon_by_world_pos(vector2)

    def get_hexagon(self, x, y):
        return self.map.get((x, y), create_hexagon(0, (x, y), GRASS))

    def convert_map(self, map):
        for hexagon in map["hexagons"]:
            hexagon_pos = hexagon["x"], hexagon["y"]
            attrs = hexagon["attributes"]
            hexagon_type = hexagon["type"] if hexagon["type"] != BUILDING else attrs["struct"]
            del attrs["struct"]
            self.map[hexagon_pos] = create_hexagon(
                get_game().get_current_fight().get_player(),
                hexagon_pos, hexagon_type, *attrs)
        print(self.map)

    # def get_current_hexagon_sprite(data):
    #     if data["type"] == BUILDING:
    #         return data["attributes"]["struct"]


# map = {(3, 3): {"type":
#                 }}
map = json.loads(open("test.json").read())


def get_game():
    return game


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    myfont = pygame.font.SysFont('Comic Sans MS', 22)
    size = width, height = 800, 600
    screen = pygame.display.set_mode(size)
    game = Game(screen)
    game.init_pygame_variables()
    running = True
    clock = pygame.time.Clock()
    game.create_fight(map)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # res = game.get_click(event.pos)
                # print(event.pos)
                # print(res)
                game.on_click(pygame.Vector2(event.pos))
                pass
        pressed = pygame.key.get_pressed()
        # print(pressed)
        # if any(pressed):
        game.buttons_handler(pressed)
        game.tick()
        game.flip()
        pygame.display.flip()
        clock.tick(FPS)
        # size = width, height = pygame.display.get_surface().get_size()

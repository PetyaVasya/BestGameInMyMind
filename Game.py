from __future__ import annotations

import datetime
import random
from threading import Thread
from time import sleep
from typing import Optional
from shapely.geometry import MultiPoint
from shapely.ops import nearest_points

from Tools import *
from Client import Client
from UI import *
from Environment import *
from constants import *
from Settings import SessionAttributes
from math import sin, cos, radians
from copensimplex import OpenSimplex

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


class SingletonMeta(type):
    """
    В Python класс Одиночка можно реализовать по-разному. Возможные способы
    включают себя базовый класс, декоратор, метакласс. Мы воспользуемся
    метаклассом, поскольку он лучше всего подходит для этой цели.
    """

    _instance: Optional[Game] = None

    def __call__(self) -> Game:
        if self._instance is None:
            self._instance = super().__call__()
        return self._instance


class Game(metaclass=SingletonMeta):
    hexagons = {}

    def __init__(self):
        self._surface = None
        self.session: GameSession = None
        self.center = pygame.Vector2(0, 0)
        self.tips = {}
        self.client = Client()
        self.sets = {}
        self.screen: ScreensSystem = None
        self.STATUSBAR_FONT = STATUSBAR_FONT
        self.STANDARD_FONT = STANDARD_FONT

    @property
    def surface(self):
        return self._surface

    @surface.setter
    def surface(self, value):
        self._surface = value
        if not self.screen:
            self.screen: ScreensSystem = ScreensSystem(value)
        else:
            self.screen.main_surface = value

    def init_pygame_variables(self):
        self.center = pygame.Vector2(
            self.surface.get_width() / 2 // STANDARD_WIDTH * STANDARD_WIDTH,
            self.surface.get_height() / 2 // STANDARD_HEIGHT * STANDARD_HEIGHT)
        self.hexagons = {GRASS: load_image(SPRITES_PATHS[GRASS]),
                         WATER: load_image(SPRITES_PATHS[WATER]),
                         }
        n_size = self.surface.get_size()
        size = pygame.Vector2(n_size)
        self.tips = {k: Tip(v["title"], v["text"]) for k, v in tips.items()}
        self.sets[GHOST] = load_image_set("./images/anim_sets/ghost", [STANDARD_WIDTH // 2] * 2)

    def flip(self):
        if self.screen.current != "offline" and self.screen.current != "game":
            self.screen.flip()
        else:
            if self.session and not self.session.ended:
                self.screen.flip()
            else:
                self.screen.overlay.flip()

    def mouse_flip(self, pos):
        if self.session:
            self.session.mouse_flip(pos)
        self.screen.mouse_flip(pos)

    def tick(self, delta):
        if self.screen.current != "offline" and self.screen.current != "game":
            self.screen.tick(delta)
        else:
            self.screen.overlay.tick(delta)

    def buttons_handler(self, events):
        self.screen.check_pressed(events)

    def get_click(self, mouse_pos):
        self.screen.get_click(mouse_pos)

    def create_fight(self, seed=None, extra=None, player=1, players=2):
        if seed:
            self.session = GameSession(self.surface, ONLINE, players=players)
            print("CURRENT PLAYER: ", player)
            self.session.player = player
            self.session.generate_map(seed, extra)
            self.screen.add_screen("game", Screen(self.surface.get_size())
                                   .add_object((0, 0), self.session))
        else:
            self.session = GameSession(self.surface)
            self.session.generate_map()
            self.screen.add_screen("offline", Screen(self.surface.get_size())
                                   .add_object((0, 0), self.session))

    def end_game(self, win=False):
        if self.session:
            self.session.ended = True
            s = Dialog(self.screen.overlay.surface, "Вы победили!" if win else "Вы проиграли",
                       title="Конец игры", buttons=OK_BUTTON, width=210, height=210,
                       align=CENTER)
            self.screen.current = "main"
            # s.action = go_main
            self.screen.overlay.add_object(pygame.Vector2(), s)


class ResourceSystem:

    def __init__(self):
        self._wood = START_WOOD
        self._rocks = START_ROCKS
        self._men = 0

    @property
    def wood(self):
        return self._wood

    @wood.setter
    def wood(self, value):
        self._wood = value
        Game().session.statusbar["wood"].value = value

    @property
    def rocks(self):
        return self._rocks

    @rocks.setter
    def rocks(self, value):
        self._rocks = value
        Game().session.statusbar["rocks"].value = value

    @property
    def men(self):
        return self._men

    @men.setter
    def men(self, value):
        self._men = value
        Game().session.statusbar["men"].value = value

    def build(self, hexagon: int) -> bool:
        needed = RESOURCES_FOR_BUILD[hexagon][:2]
        if (self.wood >= needed[0]) and (self.rocks >= needed[1]):
            self.wood -= needed[0]
            self.rocks -= needed[1]
            return True
        return False


def tick(session: GameSession):
    while not session.field:
        pass
    clock = pygame.time.Clock()
    while not session.ended:
        session.tick(clock.tick() / 1000)
    sleep(1)
    Game().session = None


class GameSession:

    def __init__(self, screen, mode=OFFLINE, players=2):
        self.field: Field = None
        self.mode = mode
        self._screen = screen
        self.attributes = SessionAttributes()
        self.finished = False
        self.shift = pygame.Vector2(0, 0)
        self.selected = None
        self.menu: GameMenu = GameMenu(self.screen, width=screen.get_width())
        self.menu.set_world_position(0, screen.get_height() - STANDARD_WIDTH * 2.5)
        self.statusbar: Statusbar = Statusbar(self.screen, width=screen.get_width())
        self.game_mode = NORMAL
        self.statusbar.set_bar("wood", START_WOOD, load_image(SPRITES_PATHS[WOOD]))
        self.statusbar.set_bar("rocks", START_ROCKS, load_image(SPRITES_PATHS[ROCK]))
        self.statusbar.set_bar("men", 0, load_image(SPRITES_PATHS[MEN]))
        self.resources = ResourceSystem()
        self.pseudo_path = None
        self.player = 1
        self.players = players
        self.seed = None
        self.web = Web()
        self.ended = False
        self.alive = True
        self.leave_dialog = None
        self.game_animations = Screen((50.5 * STANDARD_WIDTH, 101 * STANDARD_HEIGHT))
        self.thread = Thread(target=tick, args=(self,))
        self.thread.start()

    @property
    def screen(self):
        return self._screen

    @screen.setter
    def screen(self, value):
        self._screen = value
        if self.field:
            self.field.screen = value
        self.menu.screen = value
        self.statusbar.screen = value

    def generate_map(self, seed=None, extra=None):
        if seed:
            self.field = Field(self.screen, seed, extra, players=self.players)
        else:
            self.seed = int(random.random() * 1e16)
            self.field = Field(self.screen, self.seed, {
                "session": 0,
                "hexagons":
                    [
                        {
                            "x": 0,
                            "y": 0,
                            "type": BUILDING,
                            "player": 1,
                            "attributes":
                                {
                                    "struct": CASTLE
                                }
                        },
                        {
                            "x": 6,
                            "y": 0,
                            "type": BUILDING,
                            "player": 2,
                            "attributes":
                                {
                                    "struct": CASTLE
                                }
                        }
                    ]
            })

    def increase_shift(self, x, y):
        self.shift.x -= x
        self.shift.y -= y

    def get_click(self, pos):
        if self.ended:
            return
        if pos.y < 20:
            return
        elif pos.y > (self.screen.get_height() - STANDARD_WIDTH * 2.5):
            self.menu.on_click(pos)
            return
        real_pos = pos - self.shift
        clicked_pos = self.field.get_click(real_pos)
        clicked = self.field.get_hexagon(*clicked_pos)
        if self.game_mode == PATH_MAKING and pygame.key.get_mods() & pygame.KMOD_CTRL:
            if (len(self.pseudo_path.points) > 1) \
                    and not LineString(self.pseudo_path.global_points).buffer(2).intersection(
                Point(*real_pos)).is_empty:
                point = nearest_points(MultiPoint(self.pseudo_path.global_points),
                                       Point(*real_pos))[0]
                self.pseudo_path.remove_point((point.x, point.y), True)
        elif self.game_mode == PATH_MAKING and clicked is not self.selected and (
                clicked.type != BUILDING or clicked.player != self.player
                or clicked.building_type == PROJECT):
            path_points = LineString(list(self.pseudo_path.points) + [clicked_pos])
            if self.field.water.intersection(path_points).is_empty and ((
                    len(self.pseudo_path.points) == 1 or path_points.is_simple)):
                self.pseudo_path.add_point(clicked_pos)
            return
        elif self.game_mode == PATH_MAKING:
            return
        if self.menu.action == DESTROY and clicked.type == BUILDING \
                and clicked.player == self.player and not isinstance(clicked, Castle):
            if self.mode == ONLINE:
                client = Game().client
                client.add_action(client.destroy_building(clicked.hexagon))
            if isinstance(clicked, Project) and clicked.hp.is_empty():
                r = RESOURCES_FOR_BUILD[clicked.building.building_type]
                self.resources.wood += r[0]
                self.resources.rocks += r[1]
            clicked.destroy()
            if not pygame.key.get_mods() & pygame.KMOD_SHIFT:
                self.menu.clear()
        elif self.menu.action == BUILD and self.menu.build and clicked.type == GRASS\
                and self.resources.build(self.menu.build.building.building_type):
            self.field.set_hexagon(self.menu.build)
            self.menu.build.set_hexagon(clicked_pos)
            self.menu.build.building.selected = False
            if not pygame.key.get_mods() & pygame.KMOD_SHIFT:
                self.menu.clear()
            else:
                self.menu.build = self.menu.build.copy()
                self.menu.build.building.selected = True
        elif self.menu.action == MAKE_PATH and clicked.type == BUILDING\
                and clicked.player == self.player and isinstance(clicked, UnitSpawn):
            self.game_mode = PATH_MAKING
            if len(clicked.path.points) > 1:
                self.pseudo_path = clicked.path.copy()
            else:
                self.pseudo_path = Path(deque([clicked_pos]), player=self.player)
            self.selected = clicked
            self.menu.action = ASK
        elif self.menu.action == DELETE_PATH:
            clicked = self.web.get_clicked(real_pos)
            if clicked:
                point = nearest_points(MultiPoint(clicked[1].global_points),
                                       Point(*real_pos))[0]
                removed = clicked[1].remove_point((point.x, point.y), True)
                if self.mode == ONLINE:
                    client = Game().client
                    client.add_action(client.make_path(clicked[1].points[0], removed, []))
        elif not self.menu.action and clicked.type == BUILDING and clicked.player == self.player:
            self.selected = clicked
            self.selected.selected = True
        elif not self.menu.action and self.selected:
            self.selected.selected = False
            self.selected = None

    def make_menu(self, hexagon=None):
        if hexagon:
            pass
        else:
            pass

    def end_path_making(self, result):
        if result:
            if self.mode == ONLINE:
                ma_le = min(len(self.selected.path.points), len(self.pseudo_path.points))
                c = 0
                for i in range(ma_le):
                    if self.selected.path.points[i] != self.pseudo_path.points[i]:
                        break
                    c += 1
                client = Game().client

                old_path = self.selected.path.copy()
                old = self.selected

                def rollback(x):
                    print("END PATH", x)
                    try:
                        if x == 200:
                            pass
                        elif isinstance(x, dict):
                            print("rolbachishe")
                            self.resources.wood = x["wood"]
                            self.resources.rocks = x["rocks"]
                            old.path = old_path
                            # clicked[1].points = old_path.points
                    except Exception as e:
                        print(e)

                client.add_action(
                    client.make_path(self.pseudo_path.points[0], len(self.selected.path.points) - c,
                                     list(
                                         islice(self.pseudo_path.points, c,
                                                len(self.pseudo_path.points)))), rollback, True)
            self.selected.path = self.pseudo_path.copy()
        else:
            pass
        self.selected = None
        self.game_mode = NORMAL
        self.pseudo_path = None

    def action_handler(self, action, *attrs):
        if action == MAKE_PATH:
            func = self.selected.add_path_point
        func(*attrs)

    def __bool__(self):
        return not self.finished

    def flip(self):
        if self.field:
            self.field.flip(self.shift)
            if self.menu.build and (20 <= pygame.mouse.get_pos()[1] <= (
                    self.screen.get_height() - STANDARD_WIDTH * 2.5)):
                self.menu.build.building.paint(self.screen, self.shift)
            g = Game()
            self.game_animations.surface.fill(0)
            self.game_animations.flip()
            np = pygame.Vector2(g.session.game_animations.surface.get_size()) / 2 \
                 - self.shift + [0, 20]
            self.screen.blit(self.game_animations.surface, (0, 20),
                             pygame.Rect(*np, self.screen.get_width(), (
                                     self.screen.get_height() - STANDARD_WIDTH * 2.5)))
            self.web.flip(self.screen, self.shift,
                          self.selected if self.pseudo_path is None else None,
                          all=self.menu.action == DELETE_PATH)
        if self.pseudo_path is not None:
            self.pseudo_path.paint(self.screen, self.shift, True)
        self.menu.flip()
        self.statusbar.flip()

    def mouse_flip(self, pos):
        if pos.y < 20:
            hovered = self.statusbar.get_click(pos)
            to_paint = 0
            if not hovered:
                return
            if hovered[0] == "wood":
                to_paint = WOOD
            elif hovered[0] == "rocks":
                to_paint = ROCK
            elif hovered[0] == "men":
                to_paint = MEN
            if to_paint:
                Game().tips.get(to_paint).paint(self.screen, pos)
        elif pos.y > (self.screen.get_height() - STANDARD_WIDTH * 2.5):
            hovered = Game().tips.get(self.menu.get_hexagon_by_pos(pos))
            if hovered:
                hovered.paint(self.screen, pos)
        elif self.menu.build:
            hex_pos = self.field.get_click(pos - self.shift)
            if self.field.get_hexagon(*hex_pos).type == GRASS:
                self.menu.build.set_hexagon(hex_pos)

    def check_pressed(self, pressed):
        self.increase_shift(-20 * (pressed[pygame.K_a] or pressed[pygame.K_LEFT]) + 20 * (
                pressed[pygame.K_d] or pressed[pygame.K_RIGHT]),
                            -20 * (pressed[pygame.K_w] or pressed[pygame.K_UP]) + 20 * (
                                    pressed[pygame.K_s] or pressed[pygame.K_DOWN]))

    def mouse_up(self):
        self.screen.mouse_up()

    def tick(self, delta):
        if self.field:
            self.field.tick(delta)
            self.game_animations.tick(delta)
        men = 0
        for path in list(self.web.values()):
            if self.player == path.player:
                men += len(path)
        self.resources.men = men
        self.web.tick(delta)

    def k_down(self, event):
        if self.leave_dialog:
            return
        if event.key == pygame.K_ESCAPE:
            if self.mode == ONLINE and not self.ended:
                g = Game()
                self.leave_dialog = Dialog(g.screen.overlay.surface,
                                           "Вы действительно хотите сдаться?",
                                           title="Выход", buttons=OK_BUTTON | CANCEL_BUTTON,
                                           width=210, height=210,
                                           align=CENTER)

                def go_main(btn):
                    self.leave_dialog = None
                    if btn == OK_BUTTON:
                        g.client.add_action(g.client.surrender())
                        g.session.ended = True
                        g.screen.current = "main"

                self.leave_dialog.action = go_main
                g.screen.overlay.add_object(pygame.Vector2(), self.leave_dialog)
            elif self.mode == OFFLINE:
                g = Game()
                self.leave_dialog = Dialog(g.screen.overlay.surface,
                                           "Вы действительно хотите выйти?",
                                           title="Выход", buttons=OK_BUTTON | CANCEL_BUTTON,
                                           width=210,
                                           height=210,
                                           align=CENTER)

                def go_main(btn):
                    self.leave_dialog = None
                    print(btn)
                    if btn == OK_BUTTON:
                        g.session.ended = True
                        g.screen.current = "main"

                self.leave_dialog.action = go_main
                g.screen.overlay.add_object(pygame.Vector2(), self.leave_dialog)

    def add_animation(self, animation):
        self.game_animations.add_object(animation.world_position, animation)


class Field:

    def __init__(self, screen, seed, extra=None, start=(0, 0), players=2):
        self.start = start
        self.screen = screen
        self.width = STANDARD_WIDTH // 2
        self.height = STANDARD_HEIGHT
        self.map = {}
        self.reachable = set()
        self.water: LineString = None
        self.generate_map(seed, extra, 0 if Game().session.mode == OFFLINE else players)
        self.tiles = []
        self.myfont = pygame.font.SysFont('Comic Sans MS', Game().STANDARD_FONT)

    def tick(self, delta):
        run = tuple(self.map.values())
        for i in run:
            if i.type == BUILDING and i.building_type != PROJECT:
                i.tick(delta)

    def flip(self, shift=pygame.Vector2(0, 0)):
        self.tiles = []
        sdv = shift.x // STANDARD_WIDTH, shift.y // STANDARD_HEIGHT
        game = Game()
        ma = int(game.center.y // STANDARD_WIDTH * 2)
        for j in range(int(game.center.y // STANDARD_WIDTH * -2),
                       int(game.center.y // STANDARD_WIDTH * 2)):
            for i in range(int(game.center.x // STANDARD_WIDTH * -2),
                           int(game.center.x // STANDARD_WIDTH * 2)):
                if j:
                    c_hex = ((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma, j - sdv[1])
                    current = self.map.get(c_hex, GRASS if (-50 <= c_hex[0] <= 50) and (
                            -50 <= c_hex[1] <= 50) else create_hexagon(0, c_hex, WATER))
                    if current == GRASS:
                        current_hexagon = game.hexagons[GRASS]
                        r = self.screen.blit(current_hexagon, (
                            game.center.x + i * STANDARD_WIDTH + 32 * (
                                    abs(j) - abs(sdv[1]) % ma) + shift.x % STANDARD_WIDTH,
                            game.center.y + (j * STANDARD_HEIGHT) + shift.y % STANDARD_HEIGHT))
                        self.tiles.append(r)
                        textsurface = self.myfont.render(
                            '{}, {}'.format((i - sdv[0]) * 2 + abs(j) - abs(sdv[1]) % ma,
                                            j - sdv[1]), False, (0, 0, 0))
                        self.screen.blit(textsurface,
                                         (game.center.x + i * STANDARD_WIDTH + 32 * (
                                                 abs(j) - abs(sdv[1]) % ma) + shift[
                                              0] % STANDARD_WIDTH + 16,
                                          game.center.y + (j * STANDARD_HEIGHT) + shift[
                                              1] % STANDARD_HEIGHT + 32))
                    else:
                        current.paint(self.screen, shift)
                else:
                    c_hex = ((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1])
                    current = self.map.get(c_hex, GRASS if (-50 <= c_hex[0] <= 50) and (
                            -50 <= c_hex[1] <= 50) else create_hexagon(0, c_hex, WATER))
                    if current == GRASS:
                        current_hexagon = game.hexagons[GRASS]
                        self.tiles.append(self.screen.blit(current_hexagon,
                                                           (
                                                               game.center.x + i * STANDARD_WIDTH +
                                                               shift.x % STANDARD_WIDTH + 32 * (
                                                                       sdv[1] % 2),
                                                               game.center.y
                                                               + shift.y % STANDARD_HEIGHT)
                                                           )
                                          )
                        textsurface = self.myfont.render(
                            '{}, {}'.format((i - sdv[0]) * 2 + (sdv[1] % 2), -sdv[1]),
                            False, (0, 0, 0))
                        self.screen.blit(textsurface, (
                            game.center.x + i * STANDARD_WIDTH + shift.x % STANDARD_WIDTH + 32 * (
                                    sdv[1] % 2) + 16,
                            game.center.y + shift.y % STANDARD_HEIGHT + 32))
                    else:
                        current.paint(self.screen, shift)

    def get_click(self, vector2):
        return get_hexagon_by_world_pos(vector2)

    def check_pressed(self, pressed):
        pass

    def mouse_flip(self, pos):
        pass

    def get_hexagon(self, x, y) -> Hexagon:
        return self.map.get((x, y),
                            create_hexagon(0, (x, y),
                                           GRASS if -50 <= x <= 50 and -50 <= y <= 50 else WATER))

    def generate_map(self, seed, extra=None, players=2):
        start = datetime.datetime.now()
        if extra is None:
            extra = {"hexagons": []}
        gen = OpenSimplex(seed)

        def noise(nx, ny):
            return gen.noise2d(nx, ny)

        def biome(e):
            if e < 0.2:
                return WATER
            else:
                return GRASS

        height = 50
        width = 50
        R = 2
        CR = 15
        mapp = {}
        trees = {}
        mines = {}
        castles = {}
        g = Game()
        cells = width * height * 4
        now = 0
        for y in range(-height, height + 1):
            for x in range(-width, width + 1):
                if (x % 2) != (y % 2):
                    continue
                nx = x / width
                ny = y / height
                mapp[(x, y)] = (1 + min(1, 1 * noise(1 * nx, 1 * ny) \
                                        + 0.5 * noise(2 * nx, 2 * ny) \
                                        + 0.25 * noise(4 * nx, 4 * ny)) - euclidean(
                    pygame.Vector2(), pygame.Vector2(nx, ny) * 1.1) ** 5) / 2
                trees[(x, y)] = noise(20 * nx, 20 * ny)
                mines[(x, y)] = noise(10 * nx, 10 * ny)
                castles[(x, y)] = noise(10 * nx, 10 * ny)
        full = [(i["x"], i["y"]) for i in extra["hexagons"]]
        real_castles = []
        was = []
        for y in range(-height, height + 1):
            for x in range(-height, height + 1):
                now = round(now + 100 / cells, 2)
                if not now % 5:
                    print("Field loaded on: {}%".format(int(now)))
                if (x % 2) != (y % 2):
                    continue
                new = biome(mapp[(x, y)])
                mmt = -5
                mmm = -5
                mmc = -5
                for i in range(max(-height, y - R), min(y + R, height + 1)):
                    for j in range(max(-width, x - R), min(x + R, width + 1)):
                        if (i % 2) != (j % 2):
                            continue
                        mmt = max(trees[(j, i)], mmt)
                        mmm = max(mines[(j, i)], mmm)
                for i in range(max(-height, y - CR), min(y + CR, height + 1)):
                    for j in range(max(-width, x - CR), min(x + CR, width + 1)):
                        if (j % 2) != (i % 2) or (j, i) in was:
                            continue
                        mmc = max(castles[(j, i)], mmc)
                if (x, y) in full:
                    continue
                if new != WATER:
                    if castles[(x, y)] == mmc:
                        real_castles.append(
                            {"x": x, "y": y, "type": BUILDING,
                             "attributes": {"struct": CASTLE}})
                        was.append((x, y))
                    elif trees[(x, y)] == mmt:
                        extra["hexagons"].append(
                            {"x": x, "y": y, "type": RESOURCE, "attributes": {"resource": FOREST}})
                    elif mines[(x, y)] == mmm:
                        extra["hexagons"].append(
                            {"x": x, "y": y, "type": RESOURCE, "attributes": {"resource": MINE}})
                elif new != GRASS:
                    self.map[(x, y)] = create_hexagon(0, (x, y), new)
        self.convert_map(extra)
        self.reachable = set()
        que = [(0, 0)]
        water = None
        while que:
            cur = que.pop()
            for new_position in [(-2, 0), (-1, -1), (1, -1), (2, 0), (1, 1),
                                 (-1, 1)]:  # Adjacent squares

                # Get node position
                node_position = (
                    cur[0] + new_position[0],
                    cur[1] + new_position[1])
                hexagon = self.get_hexagon(*node_position)
                if hexagon.type != WATER:
                    le = len(self.reachable)
                    self.reachable.add(node_position)
                    if le != len(self.reachable):
                        que.append(node_position)
                elif not water:
                    water = node_position
        que.append(water)
        water_points = []
        while que:
            cur = que.pop()
            for new_position in [(-2, 0), (-1, -1), (1, -1), (2, 0), (1, 1),
                                 (-1, 1)]:  # Adjacent squares

                # Get node position
                node_position = (
                    cur[0] + new_position[0],
                    cur[1] + new_position[1])
                hexagon = self.get_hexagon(*node_position)

                def get_neighbors(pos):
                    return [self.get_hexagon(
                        pos[0] + x // (abs(y) + 1), pos[1] + y) for x in
                        range(-2, 3, 2) for y in
                        range(-1, 2) if (x != 0) and not (x == y == 0)]

                if hexagon.type == WATER and any(
                        map(lambda x: x.type == GRASS, get_neighbors(node_position))):
                    if node_position not in water_points:
                        water_points.append(node_position)
                        que.append(node_position)
                elif not water:
                    water = node_position
        self.water = LineString(water_points)
        random.seed(seed)
        new_extra = {"hexagons": []}
        for player, castle in enumerate(random.sample(
                list(filter(lambda x: (x["x"], x["y"]) in self.reachable, real_castles)), players),
                1):
            castle["player"] = player
            new_extra["hexagons"].append(castle)
            if player == g.session.player:
                g.session.shift = (get_hexagon_pos(castle["x"], castle["y"], False) - g.center) * -1
            print("CASTLE ON: {}".format((castle["x"], castle["y"])))
        self.convert_map(new_extra)
        print(datetime.datetime.now() - start)

    def convert_map(self, changes):
        for hexagon in changes["hexagons"]:
            hexagon_pos = hexagon["x"], hexagon["y"]
            attrs = hexagon["attributes"].copy()
            if hexagon["type"] == BUILDING:
                hexagon_type = attrs["struct"]
                del attrs["struct"]
            elif hexagon["type"] == RESOURCE:
                hexagon_type = attrs["resource"]
                del attrs["resource"]
            else:
                hexagon_type = hexagon["type"]
            self.map[hexagon_pos] = create_hexagon(
                hexagon.get("player", 0),
                hexagon_pos, hexagon_type,
                *(list(attrs.values())[0].values() if hexagon_type == PROJECT else attrs.values()))

    def intersect_hexagon(self, pos, player):
        hexagon = self.get_hexagon(*pos)
        if isinstance(hexagon, Source):
            hexagon.increase(player)
            return True
        elif isinstance(hexagon, Project):
            hexagon = hexagon.intersect(player)
            if hexagon:
                self.map[pos] = hexagon
            return True
        elif Building in hexagon.__class__.__bases__ or UnitSpawn in hexagon.__class__.__bases__:
            hexagon.intersect(player)
            return True
        return False

    def set_hexagon(self, hexagon):
        self.map[hexagon.hexagon] = hexagon

    def get_2d_map(self):
        return [[self.map.get((j, i), 0) for i in range(-50, 51)] for j in range(-50, 51)]


class Presets:

    def __init__(self):
        pass


def get_hexagon_by_world_pos(vector2):
    vector2 = pygame.Vector2(vector2) - Game().center
    current = [int(vector2.x // (STANDARD_WIDTH // 2)),
               int(vector2.y // STANDARD_HEIGHT)]
    current = current[0] - ((current[0] % 2) ^ (current[1] % 2)), current[1]
    point = Point(vector2.x, vector2.y)
    polygon = Polygon(
        [(current[0] * (STANDARD_WIDTH // 2) + round(sin(radians(i))) * (
                STANDARD_WIDTH // 2) + STANDARD_WIDTH // 2,
          current[1] * STANDARD_HEIGHT + round(cos(radians(i)) * (STANDARD_WIDTH // 2)) + (
                  STANDARD_WIDTH // 2)) for i in
         range(0, 360, 60)])
    if polygon.contains(point):
        return current[0], current[1]
    else:
        if (vector2.x % STANDARD_WIDTH) > (STANDARD_WIDTH // 2):
            return current[0] - 1 * (-1 if (current[1] % 2) == 0 else 1), current[1] - 1
        else:
            return current[0] + 1 * (-1 if (current[1] % 2) == 0 else 1), current[1] - 1


def get_hexagon_pos(x, y, with_shift=True):
    game = Game()
    return pygame.Vector2(x * STANDARD_WIDTH // 2 + STANDARD_WIDTH // 2,
                          y * STANDARD_HEIGHT + STANDARD_WIDTH // 2) + game.center + (
               game.session.shift if game.session and with_shift else [0, 0])


def create_hexagon(player, hexagon, hex_type, *args):
    if hex_type == CASTLE:
        return Castle(player, hexagon)
    elif hex_type == STORAGE:
        return Storage(player, hexagon, *args)
    elif hex_type == ROAD:
        return Road(player, hexagon)
    elif hex_type == FOREST:
        return Source(hex_type, hexagon)
    elif hex_type == MINE:
        return Source(hex_type, hexagon)
    elif hex_type == WATER:
        n = Hexagon(hex_type, hexagon)
        n.set_sprite(Game().hexagons[WATER])
        return n
    elif hex_type == GRASS:
        return Hexagon(hex_type, hexagon)
    elif hex_type == PROJECT:
        return Project(player, hexagon, create_hexagon(player, hexagon, *args),
                       RESOURCES_FOR_BUILD[args[0]][2])
    elif hex_type == CANTEEN:
        return Canteen(player, hexagon)
    elif hex_type == BARRACKS:
        return UnitSpawn(player, BARRACKS, hexagon)
    elif hex_type == TOWER:
        return Tower(player, hexagon)

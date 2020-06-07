from __future__ import annotations
from collections import deque
import datetime
from itertools import islice
import random
from typing import Optional

import discord
import pygame
from pygame.threads import Thread
from shapely.geometry import LineString, Point, MultiPoint
from shapely.ops import nearest_points
from shapely.geometry.polygon import Polygon

from app import app
from .Tools import *
from .Environment import *
from .game_constants import *
from .Settings import SessionAttributes
from math import sin, cos, radians
from .copensimplex import OpenSimplex
from queue import PriorityQueue
from threading import current_thread

from .. import models
from ..constants import FINISHED, ONLINE
from ..models import User

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

    _instance: Optional[ServerGame] = None

    def __call__(self) -> ServerGame:
        if self._instance is None:
            self._instance = super().__call__()
        return self._instance


class ServerGame(metaclass=SingletonMeta):
    hexagons = {}

    def __init__(self):
        self.sessions = {}
        self.center = pygame.Vector2(0, 0)

    def tick(self, delta):
        for session in list(self.sessions.values()):
            session.tick(delta)

    def create_fight(self, sid, seed, players, extra=None):
        self.sessions[sid] = GameSession(sid, players)
        self.sessions[sid].generate_map(seed, extra)

    def end_game(self, sid, winner):
        self.sessions[sid].ended = True
        self.sessions[sid].winner = winner


class Player:

    def __init__(self, num):
        self.num = num
        self.wood = START_WOOD
        self.rocks = START_ROCKS
        self.men = 0

    def __eq__(self, other):
        if isinstance(other, int):
            return self.num == other
        elif isinstance(other, Player):
            return self.num == other.num
        else:
            raise TypeError("Only player or int")

    def build(self, hexagon: int) -> bool:
        needed = RESOURCES_FOR_BUILD[hexagon][:2]
        if (self.wood >= needed[0]) and (self.rocks >= needed[1]):
            self.wood -= needed[0]
            self.rocks -= needed[1]
            return True
        return False


class ResourceSystem(dict):

    def __init__(self, players=2):
        super().__init__()
        for p in range(1, players + 1):
            self[p] = Player(p)

    def build(self, player, hexagon: int) -> bool:
        return self[player].build(hexagon)


def send_session_end(s):
    try:
        webhook = discord.Webhook.partial(app.app.config["WEBHOOK_SESSION_ID"],
                                          app.app.config["WEBHOOK_SESSION_TOKEN"],
                                          adapter=discord.RequestsWebhookAdapter())
        embed = discord.Embed()
        embed.title = "Сессия #{}".format(s.id)
        embed.colour = discord.Colour.darker_grey()
        embed.description = "Результаты игры"
        winner = "{} | <@!{}>".format(s.winner.name, s.winner.discord_id) if s.winner.discord_id \
            else s.winner.name
        embed.add_field(name="Победитель:",
                        value=winner)
        embed.add_field(name="Игроки:",
                        value=", ".join(map(lambda x: x[0],
                                            s.users.with_entities(User.name).all())))
        webhook.send(embed=embed)
    except Exception as e:
        print(e)


def tick(session: GameSession):
    while not session.seed and not session.ended:
        pass
    if session.ended:
        del ServerGame().sessions[session.sid]
        return
    session.field = Field(session.seed, session.extra, session.players)
    s = models.Session.query.filter(models.Session.id == session.sid).first()
    field_created = models.SessionLogs(user=0, session=s.id, action="FIELD_CREATED",
                                       date=datetime.datetime.now())
    app.db.session.add(field_created)
    app.db.session.commit()
    clock = pygame.time.Clock()
    while not session.ended:
        session.tick(clock.tick() / 1000)
    s = models.Session.query.filter(models.Session.id == session.sid).first()
    if s and (s.status != FINISHED):
        s.status = FINISHED
        winner = s.users[session.winner - 1]
        s.winner = winner
        win_log = models.SessionLogs(user=winner.id, session=s.id, action="WIN",
                                     date=datetime.datetime.now())
        s.status = FINISHED
        app.db.session.add(win_log)
        app.db.session.commit()
        send_session_end(s)
    del ServerGame().sessions[session.sid]


class GameSession:

    def __init__(self, sid, players=2):
        # Создание сессиии и потока под нее с указанием id, чтобы можно было определить, к какой
        # сессии относится тот или иной объект
        self.field = None
        self.mode = ONLINE
        self.attributes = SessionAttributes()
        self.finished = False
        self.selected = None
        self.resources = ResourceSystem()
        self.seed = None
        self.web = Web()
        self.ended = False
        self.alive = True
        self.sid = sid
        self.winner = None
        self.players = players
        self.seed = None
        self.extra = None
        self.thread = Thread(target=tick, args=(self,))
        self.thread.name = "sid" + str(sid)
        self.thread.start()

    def generate_map(self, seed, extra=None):
        self.extra = extra
        self.seed = seed

    def __bool__(self):
        return not self.finished

    def tick(self, delta):
        if self.field:
            self.field.tick(delta)
        self.web.tick(delta)
        self.check_win()

    def build(self, player, data):
        hexagon: Building = convert_hexagon(data)
        if UnitSpawn in hexagon.building.__class__.__bases__ or isinstance(
                hexagon.building, UnitSpawn):
            self.web.register(hexagon.building)
            hexagon.building.alpha = 0.15
        hexagon.sid = self.sid
        if Building not in hexagon.__class__.__bases__:
            return False
        elif hexagon.player != player:
            return False
        elif hexagon.hexagon not in self.field.reachable:
            return False
        elif self.field.get_hexagon(*hexagon.hexagon).type == GRASS and self.resources.build(
                hexagon.player, hexagon.building.building_type):
            self.field.set_hexagon(hexagon)
            hexagon.hp += 1
            return True
        return False

    def make_path(self, player, start, removed, added):
        hexagon: UnitSpawn = self.field.get_hexagon(*start)
        if UnitSpawn not in hexagon.__class__.__bases__ and not isinstance(hexagon, UnitSpawn):
            return False
        elif hexagon.player != player:
            return False
        elif (len(hexagon.path.points) - 1) < removed:
            return False
        last = len(added) - 1
        points = []
        sliced = list(islice(hexagon.path.points, 0, len(hexagon.path.points) - removed))
        last_p = tuple(sliced[-1])
        for ind, point in enumerate(added):
            point = tuple(point)
            if not any(map(lambda x: (point[0] + x[0], point[1] + x[1]) == last_p,
                           ((-2, 0), (-1, -1), (1, -1), (2, 0), (1, 1),
                            (-1, 1)))):
                return False
            else:
                last_p = point
            if point not in self.field.reachable:
                return False
            phexagon = self.field.get_hexagon(*point)
            if ind != last:
                if phexagon.type != GRASS:
                    return False
            points.append(point)
        if not points and (removed == (len(hexagon.path.points) - 1)):
            hexagon.path = Path(deque([start]), hexagon.player)
            return True
        res_points = sliced + points
        linestring = LineString(res_points)
        if not linestring.is_simple:
            return False
        elif not self.field.water.intersection(linestring).is_empty:
            return False
        hexagon.path = Path(deque(res_points), hexagon.player)
        return True

    def destroy(self, player, hexagon):
        hexagon: Building = self.field.get_hexagon(*hexagon)
        if Building not in hexagon.__class__.__bases__:
            return False
        elif hexagon.player != player:
            return False
        elif isinstance(hexagon, Castle):
            return False
        if isinstance(hexagon, Project) and hexagon.hp.is_empty():
            res = RESOURCES_FOR_BUILD[hexagon.building.building_type]
            self.resources[player].wood += res[0]
            self.resources[player].rocks += res[1]
        hexagon.destroy()
        return True

    def check_win(self):
        castles = list(filter(lambda x: isinstance(x, Castle), list(self.field.map.values())))
        if len(castles) == 1:
            self.winner = castles[0].player
            self.ended = True
            return True
        elif len(castles) == 0:
            self.winner = 1
            self.ended = True
            return True
        return False


def convert_hexagon(hexagon):
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
    return create_hexagon(
        hexagon.get("player", 0),
        hexagon_pos, hexagon_type,
        *(list(attrs.values())[0].values() if hexagon_type == PROJECT else attrs.values()))


class Field:

    def __init__(self, seed, extra=None, start=(0, 0), players=2):
        self.start = start
        self.map = {}
        self.reachable = set()
        self.water = None
        self.sid = int(current_thread().name[3:])
        self.generate_map(seed, extra, players)
        self.tiles = []

    def tick(self, delta):
        run = tuple(self.map.values())
        for i in run:
            if i.type == BUILDING and i.building_type != PROJECT:
                i.tick(delta)

    def get_hexagon(self, x, y) -> Hexagon:
        return self.map.get((x, y),
                            create_hexagon(0, (x, y),
                                           GRASS if -50 <= x <= 50 and -50 <= y <= 50 else WATER))

    def generate_map(self, seed, extra=None, players=2):
        # Генерация игрового поля на основе seed'а и шумов Перлина
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
        full = ((i["x"], i["y"]) for i in extra["hexagons"])
        real_castles = []
        was = []
        for y in range(-height, height + 1):
            for x in range(-height, height + 1):
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
        self.convert_map(new_extra)

    def convert_map(self, changes):
        for hexagon in changes["hexagons"]:
            c_hexagon: Hexagon = convert_hexagon(hexagon)
            self.map[c_hexagon.hexagon] = c_hexagon

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
        hexagon.sid = self.sid

    def get_2d_map(self):
        return [[self.map.get((j, i), 0) for i in range(-50, 51)] for j in range(-50, 51)]


class Presets:

    def __init__(self):
        pass


def get_hexagon_by_world_pos(vector2):
    vector2 = pygame.Vector2(vector2) - ServerGame().center
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


def get_hexagon_pos(x, y):
    game = ServerGame()
    return pygame.Vector2(x * STANDARD_WIDTH // 2 + STANDARD_WIDTH // 2,
                          y * STANDARD_HEIGHT + STANDARD_WIDTH // 2) + game.center


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

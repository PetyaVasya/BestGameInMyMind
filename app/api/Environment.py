from collections import deque
from itertools import islice
from threading import current_thread

from shapely.geometry import LineString, Point

from app.api import Game
from .Tools import astar, PositionTarget
from .game_constants import *
import pygame


class Object:

    def __init__(self, hexagon=None, player=0):
        self.player = player
        self.rotation = 0
        self.hexagon = None
        if hexagon:
            self.hexagon = hexagon
            game = Game.ServerGame()
            self.world_position = pygame.Vector2(
                game.center.x + hexagon[0] * STANDARD_WIDTH // 2,
                game.center.y + hexagon[
                    1] * STANDARD_HEIGHT)
        else:
            self.world_position = pygame.Vector2(0, 0)
            self.hexagon = Game.get_hexagon_by_world_pos(self.world_position)
        try:
            self._sid = int(current_thread().name[3:])
        except Exception as e:
            self._sid = 0

    @property
    def sid(self):
        return self._sid

    @sid.setter
    def sid(self, value):
        self._sid = value

    def set_hexagon(self, hexagon):
        self.hexagon = hexagon
        game = Game.ServerGame()
        self.world_position = pygame.Vector2(
            game.center.x + hexagon[0] * STANDARD_WIDTH // 2,
            game.center.y + hexagon[
                1] * STANDARD_HEIGHT)

    def set_world_position(self, vector2):
        self.world_position = vector2
        self.hexagon = Game.get_hexagon_by_world_pos(self.world_position)


class Hexagon(Object):

    def __init__(self, hex_type, hexagon=None, player=0):
        super().__init__(hexagon=hexagon, player=player)
        self.selected = False
        self.type = hex_type

    def get_neighbors(self):
        if self.hexagon:
            return {
                (self.hexagon[0] + x // (abs(y) + 1),
                 self.hexagon[1] + y): Game.ServerGame().sessions[self.sid].field.get_hexagon(
                    self.hexagon[0] + x // (abs(y) + 1), self.hexagon[1] + y) for x in
                range(-2, 3, 2) for y in
                range(-1, 2) if (x != 0) and not (x == y == 0)}
        else:
            return {}

    def tick(self, delta):
        pass

    def __repr__(self):
        return "<Hexagon type='{}'>".format(self.type)


class Building(Hexagon):

    def __init__(self, player, building_type, hexagon=None, hp=10):
        self.building_type = building_type
        super().__init__(BUILDING, hexagon=hexagon, player=player)
        self.level = 1
        self.hp = Game.ProgressBar(hp)
        self.hp.set_value(hp)
        self.alive = True

    def destroy(self):
        self.alive = False
        del Game.ServerGame().sessions[self.sid].field.map[self.hexagon]

    def repair(self, hp=1):
        self.hp += hp

    def damage(self, hp=1):
        self.hp -= hp
        if self.hp.is_empty():
            self.destroy()

    def intersect(self, player):
        if player == self.player:
            if not self.hp.is_full():
                self.repair()
            else:
                self.man_action()
        else:
            self.damage()

    def man_action(self):
        pass

    def __hash__(self):
        return hash(str(BUILDING) + str(self.building_type) + str(self.world_position.xy))


class Project(Building):

    def __init__(self, player, hexagon, building, men):
        self.building = building
        super().__init__(player, PROJECT, hexagon, men)
        self.hp.set_value(0)

    @property
    def sid(self):
        return self._sid

    @sid.setter
    def sid(self, value):
        self._sid = value
        self.building.sid = value

    def set_hexagon(self, hexagon):
        super().set_hexagon(hexagon)
        self.building.set_hexagon(hexagon)

    def set_world_position(self, vector2):
        super().set_world_position(vector2)
        self.building.set_world_position(vector2)

    def intersect(self, player):
        super().intersect(player)
        if not self.alive:
            return None
        elif self.hp.is_full():
            # for v in list(Game.ServerGame().sessions[self.sid].web.values()):
            #     if self.hexagon in v.points:
            #         v.reposition()
            return self.building
        else:
            return self

    def __copy__(self):
        return Project(self.player, self.hexagon, self.building.copy(), self.hp.maximum)


class Source(Hexagon):

    def __init__(self, source_type, hexagon=None):
        super().__init__(RESOURCE, hexagon)
        self.source_type = source_type
        self.progress = Game.ProgressBar(TRADE[source_type])
        self.last_player = None

    def increase(self, player):
        if (self.last_player != player) and not self.progress.value:
            self.progress += 1
            self.last_player = player
        elif self.last_player == player:
            self.progress += 1
        else:
            self.progress.set_value(1)
            self.last_player = player
        if self.progress.is_full():
            game = Game.ServerGame()
            if self.source_type == FOREST:
                game.sessions[self.sid].resources[self.last_player].wood += 1
            elif self.source_type == MINE:
                game.sessions[self.sid].resources[self.last_player].rocks += 1
            self.progress.set_value(0)
            self.last_player = None

    def __hash__(self):
        return hash(str(RESOURCE) + str(self.source_type) + str(self.world_position.xy))


class Wall(Building):
    pass


class Tower(Building):

    def __init__(self, player, hexagon=None):
        super(Tower, self).__init__(player, TOWER, hexagon=hexagon)
        self.attack_rate = ATTACK_RATES[TOWER]
        self.range = ATTACK_RANGES[TOWER]
        self.shot_alpha = 0

    def tick(self, delta):
        self.shot_alpha += delta
        game = Game.ServerGame()
        mans = list(
            filter(lambda man: man[0] <= self.range and man[1].player != self.player,
                   sorted(map(lambda x: (self.world_position.distance_to(
                       x.world_position), x), game.sessions[self.sid].web.mans),
                          key=lambda
                              x: x[0], reverse=True)))
        for i in range(int(self.shot_alpha // self.attack_rate)):
            if not mans:
                break
            mans.pop()[1].kill()
            self.shot_alpha -= 1
        self.shot_alpha = min(1, self.shot_alpha)

    def __copy__(self):
        return Tower(self.player, self.hexagon)

    def man_action(self):
        self.shot_alpha += 0.1


class UnitSpawn(Building):

    def __init__(self, player, building_type, hexagon=None):
        self._sid = None
        super(UnitSpawn, self).__init__(player, building_type, hexagon=hexagon)
        try:
            Game.ServerGame().sessions[self.sid].web.register(self)
        except KeyError:
            pass
        self.alpha = 0

    @property
    def sid(self):
        return self._sid

    @sid.setter
    def sid(self, value):
        self._sid = value
        self.path.sid = value

    def set_hexagon(self, hexagon):
        # last = self.path.points[-1] if len(self.path.point) else
        Game.ServerGame().sessions[self.sid].web.unregister(self)
        super().set_hexagon(hexagon)
        Game.ServerGame().sessions[self.sid].web.register(self)
        # self.path.add_point(last)

    def set_world_position(self, vector2):
        # last = self.path.points[-1]
        Game.ServerGame().sessions[self.sid].web.unregister(self)
        super().set_world_position(vector2)
        Game.ServerGame().sessions[self.sid].web.register(self)
        # self.path.add_point(last)

    @property
    def path(self):
        return Game.ServerGame().sessions[self.sid].web[self]

    @path.setter
    def path(self, value):
        Game.ServerGame().sessions[self.sid].web[self] = value
        value.sid = self.sid

    def tick(self, delta):
        self.alpha += delta
        for i in range(
                int(self.alpha // Game.ServerGame().sessions[self.sid].attributes.spawn_rate)):
            if len(self.path.points) > 1:
                self.path.spawn_mob()
        self.alpha %= Game.ServerGame().sessions[self.sid].attributes.spawn_rate
        self.path.tick(delta)

    def destroy(self):
        super().destroy()
        del Game.ServerGame().sessions[self.sid].web[self]

    def add_path_point(self, hexagon):
        self.path.add_point(hexagon)

    def __copy__(self):
        return UnitSpawn(self.player, self.building_type, self.hexagon)

    def man_action(self):
        self.alpha += 0.5


class Castle(UnitSpawn):

    def __init__(self, player, hexagon=None):
        super().__init__(player, CASTLE, hexagon=hexagon)
        self.attack_rate = ATTACK_RATES[CASTLE]
        self.range = ATTACK_RANGES[CASTLE]
        self.shot_alpha = 0

    def intersect(self, player):
        if player == self.player:
            if not self.hp.is_full():
                pass
            else:
                self.man_action()
        else:
            self.damage()

    def tick(self, delta):
        UnitSpawn.tick(self, delta)
        self.shot_alpha += delta
        game = Game.ServerGame()
        mans = list(
            filter(lambda man: man[0] <= self.range and man[1].player != self.player,
                   sorted(map(lambda x: (self.world_position.distance_to(
                       x.world_position), x), game.sessions[self.sid].web.mans),
                          key=lambda
                              x: x[0], reverse=True)))
        for i in range(int(self.shot_alpha // self.attack_rate)):
            if not mans:
                break
            mans.pop()[1].kill()
            self.shot_alpha -= 1
        self.shot_alpha = min(1, self.shot_alpha)

    def __copy__(self):
        return Castle(self.player, self.hexagon)

    def man_action(self):
        self.alpha += 0.5
        self.shot_alpha += 0.1


class Road(Building):

    def __init__(self, player, hexagon=None):
        super().__init__(player, ROAD, hexagon)

    def on_click(self, button):
        pass


class Storage(Building):

    def __init__(self, player, capacity, hex_type, hexagon=None):
        super().__init__(player, STORAGE, hexagon)
        self.capacity = capacity
        self.type = hex_type


class Canteen(Building):

    def __init__(self, player, hexagon=None):
        super().__init__(player, CANTEEN, hexagon)

    def __copy__(self):
        return Canteen(self.player, self.hexagon)


class Path(list):

    def __init__(self, points: deque = deque(), player=1, limit=10):
        super().__init__()
        try:
            self._sid = int(current_thread().name[3:])
        except Exception as e:
            self._sid = 0
        self._points = points
        self._global_points = deque(map(lambda x: Game.get_hexagon_pos(*x), points))
        self.limit = limit
        self.player = player

    @property
    def sid(self):
        return self._sid

    @sid.setter
    def sid(self, value):
        self._sid = value
        for man in list(self):
            man.sid = value

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, value):
        self._points = value
        self._global_points = deque(map(lambda x: Game.get_hexagon_pos(*x), value))

    @property
    def global_points(self):
        return self._global_points

    @global_points.setter
    def global_points(self, value):
        self._global_points = value
        self._points = deque(map(lambda x: Game.get_hexagon_by_world_pos(x), value))

    def spawn_mob(self):
        if len(self) < self.limit:
            self.append(Man(1, 1, self.points.copy(), player=self.player))

    def add_point(self, point):
        gmap = Game.ServerGame().sessions[self.sid].field.get_2d_map()
        for p in islice(self.points, 1, len(self.points)):
            if gmap[p[0] + 50][p[1] + 50]:
                return
            else:
                gmap[p[0] + 50][p[1] + 50] = 1
        if self.points:
            if self.points[-1] == (0, 0):
                gmap[self.points[-1][0] + 50][self.points[-1][1] + 50] = 0
            gmap[point[0] + 50][point[1] + 50] = 0
            new = list(map(lambda x: (x[0] - 50, x[1] - 50),
                           astar(gmap, (self.points[-1][0] + 50, self.points[-1][1] + 50),
                                 (point[0] + 50, point[1] + 50))))[1:]
        else:
            new = [point]
        self.points.extend(new)
        self.global_points.extend(map(lambda x: Game.get_hexagon_pos(*x), new))
        for man in self:
            man.path.extend(new)

    def remove_point(self, point, global_p=False):
        if (global_p and point in self.global_points) or (not global_p and point in self.points):
            if global_p:
                point_from = max(1, self.global_points.index(point))
            else:
                point_from = max(1, self.points.index(point))
            points = list(islice(self.points, point_from, len(self.points)))
            self.points = deque(islice(self.points, point_from))
            self.global_points = deque(islice(self.global_points, point_from))
        else:
            points = []
        for man in super().copy():
            if man.get_hexagon() in points:
                man.kill()
                self.remove(man)
        return len(points)

    def tick(self, delta):
        for man in super().copy():
            if not man.tick(delta):
                self.remove(man)

    def copy(self):
        return Path(self.points.copy(), self.player, self.limit)

    def __copy__(self):
        return Path(self.points.copy(), self.player, self.limit)

    def __contains__(self, item):
        return item in self.points or item in self.global_points

    def reposition(self):
        gmap = Game.ServerGame().sessions[self.sid].field.get_2d_map()
        if self.points:
            # if self.points[-1] == (0, 0):
            #     gmap[self.points[-1][0] + 50][self.points[-1][1] + 50] = 0
            gmap[self.points[0][0] + 50][self.points[0][1] + 50] = 0
            gmap[self.points[-1][0] + 50][self.points[-1][1] + 50] = 0
            new = list(map(lambda x: (x[0] - 50, x[1] - 50),
                           astar(gmap, (self.points[0][0] + 50, self.points[0][1] + 50),
                                 (self.points[-1][0] + 50, self.points[-1][1] + 50))))
        else:
            new = [self.points[0]]
        self.points = deque(new)
        self.global_points = deque(map(lambda x: Game.get_hexagon_pos(*x), new))
        for man in self:
            man.path = self.points


class Web(dict):

    def register(self, hexagon: Hexagon):
        self[hexagon] = Path(deque([hexagon.hexagon]), hexagon.player)
        return self[hexagon]

    def unregister(self, hexagon: Hexagon):
        for m in list(self[hexagon]):
            m.kill()
        del self[hexagon]

    def get_path_by_pos(self, pos: pygame.Vector2()) -> tuple:
        for p in list(self.items()):
            if len(p[1].points) > 1 and not LineString(p[1].global_points).buffer(2).intersection(
                    Point(*pos)).is_empty:
                return tuple(p)

    def tick(self, delta):
        for path in list(self.values()):
            path.tick(delta)

    @property
    def mans(self):
        return [j for i in list(self.values()) for j in list(i)]

    def reposition(self):
        for v in list(self.values()):
            v.reposition()


class Man(Object):

    def __init__(self, hp, dmg, path, player=1):
        super().__init__(hexagon=path[0], player=player)
        self.set_hexagon(path[0])
        self.spawn = self.hexagon
        g = Game.ServerGame()
        self.life_time = g.sessions[self.sid].attributes.life_time
        self.hp = hp
        self.dmg = dmg
        self.path = path
        self.target = PositionTarget(self.world_position,
                                     Game.get_hexagon_pos(*self.hexagon) - [32, 32],
                                     STANDARD_WIDTH)
        self.alive = True

    def set_hexagon(self, hexagon):
        self.hexagon = hexagon
        game = Game.ServerGame()
        self.world_position = pygame.Vector2(
            game.center.x + hexagon[0] * (STANDARD_WIDTH // 2),
            game.center.y + hexagon[
                1] * STANDARD_HEIGHT)

    def set_world_position(self, vector2):
        self.world_position = vector2
        self.hexagon = Game.get_hexagon_by_world_pos(self.world_position + [32, 32])

    def kill(self):
        self.alive = False

    def tick(self, delta):
        if not self.alive:
            return False
        game = Game.ServerGame()
        now = game.sessions[self.sid].field.get_hexagon(
            *self.hexagon)
        if tuple(filter(lambda x: isinstance(x, Canteen) and x.player == self.player,
                        tuple(now.get_neighbors().values()) + (now,))):
            self.life_time = game.sessions[self.sid].attributes.life_time
        if self.path:
            pseudo = delta if self.life_time >= delta else self.life_time
            while pseudo > 0 and self.path:
                need = self.target.get_time_left()
                self.set_world_position(self.target.tick(pseudo % self.life_time))
                if self.target.is_reached():
                    current = self.path.popleft()
                    if self.path:
                        self.target = PositionTarget(self.world_position,
                                                     Game.get_hexagon_pos(*self.path[0]) - [
                                                         32, 32],
                                                     STANDARD_WIDTH)
                    else:
                        self.target = None
                    if current != self.spawn and game.sessions[self.sid]. \
                            field.intersect_hexagon(current, self.player):
                        self.kill()
                        return False
                pseudo -= need
        self.life_time -= delta
        if self.life_time <= 0:
            self.kill()
            return False
        return True

    def get_hexagon(self):
        return Game.get_hexagon_by_world_pos(self.world_position)

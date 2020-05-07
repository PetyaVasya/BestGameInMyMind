from collections import deque
from itertools import islice

from shapely.geometry import LineString, Point

from Tools import astar, PositionTarget
import Game
from constants import *
import pygame
from math import cos, sin, radians

from decorators import on_alive


class Object(Game.Drawable):

    def __init__(self, hexagon=None, player=0):
        self.player = player
        self.sprite = None
        self.rotation = 0
        self.hexagon = None
        if hexagon:
            self.hexagon = hexagon
            game = Game.Game()
            self.world_position = pygame.Vector2(
                game.center.x + hexagon[0] * STANDARD_WIDTH // 2,
                game.center.y + hexagon[
                    1] * STANDARD_HEIGHT)
        else:
            self.world_position = pygame.Vector2(0, 0)
            self.hexagon = Game.get_hexagon_by_world_pos(self.world_position)

    def set_hexagon(self, hexagon):
        self.hexagon = hexagon
        game = Game.Game()
        self.world_position = pygame.Vector2(
            game.center.x + hexagon[0] * STANDARD_WIDTH // 2,
            game.center.y + hexagon[
                1] * STANDARD_HEIGHT)

    def set_world_position(self, vector2):
        self.world_position = vector2
        self.hexagon = Game.get_hexagon_by_world_pos(self.world_position)

    def set_sprite(self, sprite):
        if sprite:
            self.sprite = sprite
        else:
            self.sprite = None


class Hexagon(Object):

    def __init__(self, hex_type, hexagon=None, player=0):
        super().__init__(hexagon=hexagon, player=player)
        self.selected = False
        self.type = hex_type

    def on_click(self, button):
        if button == RIGHT_CLICK:
            self.left_click()
        elif button == LEFT_CLICK:
            self.right_click()

    def right_click(self):
        pass

    def left_click(self):
        pass

    def paint(self, surface, shift):
        return surface.blit(self.sprite, self.world_position + shift)

    def get_neighbors(self):
        if self.hexagon:
            return {
                (self.hexagon[0] + x // (abs(y) + 1),
                 self.hexagon[1] + y): Game.Game().session.field.get_hexagon(
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
        self.set_sprite(Game.load_image(SPRITES_PATHS[building_type]))
        self.hp = Game.ProgressBar(hp, self.world_position)
        self.hp.set_value(hp)
        self.hp.bar_color = PLAYER_COLORS[self.player]
        self.alive = True

    def destroy(self):
        self.alive = False
        del Game.Game().session.field.map[self.hexagon]

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

    def paint(self, surface, shift):
        pygame.draw.polygon(surface, PLAYER_COLORS[self.player],
                            [self.world_position + shift + (round(sin(radians(i))) * 32 + 32,
                                                            round(cos(radians(i)) * 32) + 32) for i
                             in
                             range(0, 360, 60)])
        super().paint(surface, shift)
        if not self.hp.is_empty() and not self.hp.is_full():
            self.hp.flip(surface, shift)

    def __hash__(self):
        return hash(str(BUILDING) + str(self.building_type) + str(self.world_position.xy))


class Project(Building):

    def __init__(self, player, hexagon, building, men):
        super().__init__(player, PROJECT, hexagon, men)
        self.building = building
        self.hp.set_value(0)
        self.set_sprite(Game.load_image(SPRITES_PATHS[PROJECT]))
        self.sprite.set_alpha(127)

    def set_hexagon(self, hexagon):
        super().set_hexagon(hexagon)
        self.building.set_hexagon(hexagon)

    def set_world_position(self, vector2):
        super().set_world_position(vector2)
        self.building.set_world_position(vector2)

    def intersect(self, player):
        was = self.hp.value
        super().intersect(player)
        if not self.alive:
            return None
        if not was and self.hp.value == 1:
            self.sprite.set_alpha(255)
            g = Game.Game()
            if g.session.mode == ONLINE and self.player == g.session.player:
                client = g.client
                pos = self.hexagon

                def rollback(x):
                    print("BUILD", x)
                    try:
                        if x == 200:
                            pass
                        elif isinstance(x, dict):
                            g.session.resources.wood = x["wood"]
                            g.session.resources.rocks = x["rocks"]
                            if g.session.field.map.get(pos) and g.session.field.map[
                                pos].type == BUILDING:
                                g.session.field.map[pos].destroy()
                    except Exception as e:
                        print(e)

                client.add_action(client.build(self.hexagon, self.building_type, g.session.player,
                                               {"building": {
                                                   "building_type": self.building.building_type}}),
                                  rollback, True)
        if self.hp.is_full():
            # for v in list(Game.Game().session.web.values()):
            #     if self.hexagon in v.points:
            #         v.reposition()
            return self.building
        else:
            return self

    def paint(self, surface, shift):
        if not self.alive:
            return
        surface.blit(Game.Game().hexagons[GRASS], self.world_position + shift)
        surface.blit(self.sprite, self.world_position + shift)

    def copy(self):
        return Project(self.player, self.hexagon, self.building.copy(), self.hp.maximum)


class Source(Hexagon):

    def __init__(self, source_type, hexagon=None):
        super().__init__(RESOURCE, hexagon)
        self.source_type = source_type
        self.progress = Game.ProgressBar(TRADE[source_type], self.world_position)
        self.last_player = None
        self.set_sprite(Game.load_image(SPRITES_PATHS[source_type]))

    def increase(self, player):
        if (self.last_player != player) and not self.progress.value:
            self.progress += 1
            self.progress.bar_color = PLAYER_COLORS[player]
            self.last_player = player
        elif self.last_player == player:
            self.progress += 1
        else:
            self.progress.set_value(1)
            self.last_player = player
        if self.progress.is_full():
            game = Game.Game()
            if self.last_player == game.session.player:
                if self.source_type == FOREST:
                    game.session.resources.wood += 1
                    top_left = game.session.shift + [0, 20]
                    r = pygame.Rect(top_left.x, -top_left.y, game.session.screen.get_width(),
                                    game.session.screen.get_height() - STANDARD_WIDTH * 2.5)
                    if r.collidepoint(*self.world_position + [32, 32]):
                        resource = Game.Image(None,
                                              Game.load_image(SPRITES_PATHS[WOOD],
                                                              scale=[STANDARD_WIDTH // 4] * 2))
                        game.screen.overlay.add_object(self.world_position + top_left, resource)
                        resource.move(
                            pygame.Vector2(game.session.statusbar.get_bar_rect("wood").center), 1)
                        resource.kill_after(1)
                elif self.source_type == MINE:
                    game.session.resources.rocks += 1
                    top_left = game.session.shift + [0, 20]
                    r = pygame.Rect(top_left.x, -top_left.y, game.session.screen.get_width(),
                                    game.session.screen.get_height() - STANDARD_WIDTH * 2.5)
                    if r.collidepoint(*self.world_position + [32, 32]):
                        resource = Game.Image(None,
                                              Game.load_image(SPRITES_PATHS[ROCK],
                                                              scale=[STANDARD_WIDTH // 4] * 2))
                        game.screen.overlay.add_object(self.world_position + top_left, resource)
                        resource.move(
                            pygame.Vector2(game.session.statusbar.get_bar_rect("rocks").center), 1)
                        resource.kill_after(1)
            self.progress.set_value(0)
            self.progress.bar_color = (0, 0, 255)
            self.last_player = None

    def paint(self, surface, shift):
        super().paint(surface, shift)
        if self.progress.value and self.last_player == Game.Game().session.player:
            self.progress.flip(surface, shift)

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
        game = Game.Game()
        mans = list(
            filter(lambda man: man[0] <= self.range and man[1].player != self.player,
                   sorted(map(lambda x: (self.world_position.distance_to(
                       x.world_position), x), game.session.web.mans),
                          key=lambda
                              x: x[0], reverse=True)))
        for i in range(int(self.shot_alpha // self.attack_rate)):
            if not mans:
                break
            mans.pop()[1].kill()
            self.shot_alpha -= 1
        self.shot_alpha = min(1, self.shot_alpha)

    def copy(self):
        return Tower(self.player, self.hexagon)

    def man_action(self):
        self.shot_alpha += 0.1


class UnitSpawn(Building):

    def __init__(self, player, building_type, hexagon=None):
        super(UnitSpawn, self).__init__(player, building_type, hexagon=hexagon)
        Game.Game().session.web.register(self)
        self.alpha = 0
        self.set_sprite(Game.load_image(SPRITES_PATHS[building_type]))

    def set_hexagon(self, hexagon):
        Game.Game().session.web.unregister(self)
        super().set_hexagon(hexagon)
        Game.Game().session.web.register(self)

    def set_world_position(self, vector2):
        Game.Game().session.web.unregister(self)
        super().set_world_position(vector2)
        Game.Game().session.web.register(self)

    @property
    def path(self):
        return Game.Game().session.web[self]

    @path.setter
    def path(self, value):
        Game.Game().session.web[self] = value

    @on_alive
    def tick(self, delta):
        self.alpha += delta
        try:
            for i in range(int(self.alpha // Game.Game().session.attributes.spawn_rate)):
                if len(self.path.points) > 1:
                    self.path.spawn_mob()
            self.alpha %= Game.Game().session.attributes.spawn_rate
            self.path.tick(delta)
        except KeyError as e:
            return

    def paint(self, surface, shift):
        super().paint(surface, shift)

    def destroy(self):
        super().destroy()
        del Game.Game().session.web[self]

    def add_path_point(self, hexagon):
        self.path.add_point(hexagon)

    def copy(self):
        new = UnitSpawn(self.player, self.building_type, self.hexagon)
        new.path = self.path.copy()
        return new

    def man_action(self):
        self.alpha += 0.5


class Castle(UnitSpawn):

    def __init__(self, player, hexagon=None):
        super().__init__(player, CASTLE, hexagon=hexagon)
        self.attack_rate = ATTACK_RATES[CASTLE]
        self.range = ATTACK_RANGES[CASTLE]
        self.shot_alpha = 0

    def tick(self, delta):
        UnitSpawn.tick(self, delta)
        self.shot_alpha += delta
        game = Game.Game()
        mans = list(
            filter(lambda man: (man[0] <= self.range) and (man[1].player != self.player),
                   sorted(map(lambda x: (self.world_position.distance_to(
                       x.world_position), x), game.session.web.mans),
                          key=lambda zz: zz[0], reverse=True)))
        for i in range(int(self.shot_alpha // self.attack_rate)):
            if not mans:
                break
            mans.pop()[1].kill()
            self.shot_alpha -= 1
        self.shot_alpha = min(1, self.shot_alpha)

    def copy(self):
        new = Castle(self.player, self.hexagon)
        new.path = self.path.copy()
        return new

    def intersect(self, player):
        if player == self.player:
            if not self.hp.is_full():
                pass
            else:
                self.man_action()
        else:
            self.damage()

    def man_action(self):
        self.alpha += 0.5
        self.shot_alpha += 0.1


class Road(Building):

    def __init__(self, player, hexagon=None):
        super().__init__(player, ROAD, hexagon)
        self.set_sprite(Game.load_image(SPRITES_PATHS[ROAD]))

    def on_click(self, button):
        pass


class Storage(Building):

    def __init__(self, player, capacity, hex_type, hexagon=None):
        super().__init__(player, STORAGE, hexagon)
        self.capacity = capacity
        self.type = hex_type
        self.set_sprite(Game.load_image(SPRITES_PATHS[STORAGE]))


class Canteen(Building):

    def __init__(self, player, hexagon=None):
        super().__init__(player, CANTEEN, hexagon)
        self.set_sprite(Game.load_image(SPRITES_PATHS[CANTEEN]))

    def copy(self):
        return Canteen(self.player, self.hexagon)


class Path(list):

    def __init__(self, points: deque = deque(), player=1, limit=10):
        super().__init__()
        self._points = points
        self._global_points = deque(map(lambda x: Game.get_hexagon_pos(*x, False), points))
        self.limit = limit
        self.player = player

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, value):
        self._points = value
        self._global_points = deque(map(lambda x: Game.get_hexagon_pos(*x, False), value))

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
        g = Game.Game()
        gmap = g.session.field.get_2d_map()
        if tuple(point) not in g.session.field.reachable:
            return
        for p in islice(self.points, 1, len(self.points)):
            if gmap[p[0] + 50][p[1] + 50]:
                return
            else:
                gmap[p[0] + 50][p[1] + 50] = 1
        if self.points:
            if self.points[-1] == (0, 0):
                gmap[self.points[-1][0] + 50][self.points[-1][1] + 50] = 0
            gmap[point[0] + 50][point[1] + 50] = 0
            r = astar(gmap, (self.points[-1][0] + 50, self.points[-1][1] + 50),
                      (point[0] + 50, point[1] + 50))
            if r:
                new = list(map(lambda x: (x[0] - 50, x[1] - 50), r))[1:]
            else:
                new = []
        else:
            new = [point]
        self.points.extend(new)
        self.global_points.extend(map(lambda x: Game.get_hexagon_pos(*x, False), new))
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
        return len(points)

    def tick(self, delta):
        for man in super().copy():
            if not man.tick(delta):
                self.remove(man)

    def paint(self, surface, shift, show=False, selected=False):
        if show and len(self.points) > 1:
            for ind, i in enumerate(self.points):
                if selected:
                    pygame.draw.circle(surface, (122, 122, 0), Game.get_hexagon_pos(*i), 7)
                pygame.draw.circle(surface, (0, 0, 0), Game.get_hexagon_pos(*i), 5)
            if selected:
                pygame.draw.lines(surface, (122, 122, 0), False,
                                  list(map(lambda x: Game.get_hexagon_pos(*i), self.points)),
                                  6)
            pygame.draw.lines(surface, (0, 0, 0), False,
                              list(map(lambda x: Game.get_hexagon_pos(*x), self.points)),
                              4)
        for man in self:
            man.paint(surface, shift)

    def copy(self):
        return Path(self.points.copy(), self.player, self.limit)

    def copy(self):
        return Path(self.points.copy(), self.player, self.limit)

    def __contains__(self, item):
        return item in self.points or item in self.global_points

    def reposition(self):
        g = Game.Game()
        gmap = g.session.field.get_2d_map()
        if self.points:
            # if self.points[-1] == (0, 0):
            #     gmap[self.points[-1][0] + 50][self.points[-1][1] + 50] = 0
            gmap[self.points[0][0] + 50][self.points[0][1] + 50] = 0
            gmap[self.points[-1][0] + 50][self.points[-1][1] + 50] = 0
            if tuple(self.points[-1]) not in g.session.field.reachable:
                new = [self.points[0]]
            else:
                r = astar(gmap, (self.points[0][0] + 50, self.points[0][1] + 50),
                          (self.points[-1][0] + 50, self.points[-1][1] + 50))
                if r:
                    new = list(map(lambda x: (x[0] - 50, x[1] - 50), r))
                else:
                    new = [self.points[0]]
        else:
            new = [self.points[0]]
        self.points = deque(new)
        self.global_points = deque(map(lambda x: Game.get_hexagon_pos(*x, False), new))
        for man in self:
            man.path = self.points


class Web(dict):

    def register(self, hexagon: Hexagon):
        if self.get(hexagon):
            return self[hexagon]
        self[hexagon] = Path(deque([hexagon.hexagon]), hexagon.player)
        return self[hexagon]

    def unregister(self, hexagon: Hexagon):
        for m in list(self[hexagon]):
            m.kill()
        del self[hexagon]

    def get_clicked(self, pos: pygame.Vector2()) -> tuple:
        game = Game.Game()
        for p in filter(lambda x: x[0].player == game.session.player, list(self.items())):
            if len(p[1].points) > 1 and not LineString(p[1].global_points).buffer(2).intersection(
                    Point(*pos)).is_empty:
                return tuple(p)

    def tick(self, delta):
        for path in list(self.values()):
            path.tick(delta)

    def flip(self, surface, shift, selected, all=False):
        game = Game.Game()
        player = game.session.player
        for p in list(self.items()):
            p[1].paint(surface, shift,
                       (all or p[0] == selected) and p[1].player == player)

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
        g = Game.Game()
        self.life_time = g.session.attributes.life_time
        self.hp = hp
        self.dmg = dmg
        self.path = path
        self.target = PositionTarget(self.world_position,
                                     Game.get_hexagon_pos(*self.hexagon, False) - [32, 32],
                                     STANDARD_WIDTH)
        self.alive = True

    def set_hexagon(self, hexagon):
        self.hexagon = hexagon
        game = Game.Game()
        self.world_position = pygame.Vector2(
            game.center.x + hexagon[0] * (STANDARD_WIDTH // 2),
            game.center.y + hexagon[1] * STANDARD_HEIGHT)

    def set_world_position(self, vector2):
        self.world_position = vector2
        self.hexagon = Game.get_hexagon_by_world_pos(self.world_position + [32, 32])

    def kill(self):
        g = Game.Game()
        np = self.world_position + pygame.Vector2(g.session.game_animations.surface.get_size()) / 2
        ghost: Game.AnimatedImage = Game.AnimatedImage(None, g.sets[GHOST], 0.1, pos=np)
        ghost.kill_after(1)
        ghost.move(np - [0, 64], 1)

        # def new(x):
        #     ghost.set_alpha(x)
        # ghost.change_value(new, 255, 0, 1)
        g.session.add_animation(ghost)
        self.alive = False

    def tick(self, delta):
        if not self.alive:
            return False
        game = Game.Game()
        now = game.session.field.get_hexagon(
            *self.hexagon)
        if tuple(filter(lambda x: isinstance(x, Canteen) and x.player == self.player,
                        tuple(now.get_neighbors().values()) + (now,))):
            self.life_time = game.session.attributes.life_time
        if self.path:
            pseudo = delta if self.life_time >= delta else self.life_time
            while pseudo > 0 and self.path:
                need = self.target.get_time_left()
                self.set_world_position(self.target.tick(pseudo % self.life_time))
                if self.target.is_reached():
                    current = self.path.popleft()
                    if self.path:
                        self.target = PositionTarget(self.world_position,
                                                     Game.get_hexagon_pos(*self.path[0], False) - [
                                                         32, 32],
                                                     STANDARD_WIDTH)
                    else:
                        self.target = None
                    if current != self.spawn and game.session.field.intersect_hexagon(current,
                                                                                      self.player):
                        self.kill()
                        return False
                pseudo -= need
        self.life_time -= delta
        if self.life_time <= 0:
            self.kill()
            return False
        return True

    def paint(self, surface, shift):
        if self.alive:
            return pygame.draw.circle(surface, PLAYER_COLORS[self.player],
                                      self.world_position + shift + [32, 32],
                                      self.life_time * 2)

    def get_hexagon(self):
        return Game.get_hexagon_by_world_pos(self.world_position)


class Deliveryman(Man):

    def __init__(self, hp, life_time, start):
        super().__init__(hp, 0, life_time, deque())
        self.start = start

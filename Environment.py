from collections import deque
from Tools import load_image
import Game
from constants import *
from UI import ProgressBar
import pygame
from math import cos, sin, radians


class Object:

    def __init__(self, hexagon=None, player=0):
        self.player = player
        self.sprite = None
        self.hexagon = None
        if hexagon:
            self.set_hexagon(hexagon)
        else:
            self.world_position = pygame.Vector2(0, 0)

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

    def __init__(self, type, hexagon=None, player=0):
        super().__init__(hexagon=hexagon, player=player)
        self.selected = False
        self.type = type

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

    def tick(self):
        pass


class Building(Hexagon):

    def __init__(self, player, building_type, hexagon=None, hp=10):
        super().__init__(BUILDING, hexagon, player=player)
        self.level = 1
        self.building_type = building_type
        self.set_sprite(load_image(SPRITES_PATHS[building_type]))
        self.hp = ProgressBar(hp, self.world_position)
        self.alive = True

    def destroy(self):
        self.alive = False

    def left_click(self):
        Game.Game().session.set_selected(self)
        # self.selected = True

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
    # def upgrade(self):


class Project(Building):

    def __init__(self, player, hexagon, building, men):
        super().__init__(player, PROJECT, hexagon, men)
        self.building = building
        self.hp.set_value(0)
        self.set_sprite(load_image(SPRITES_PATHS[PROJECT]))
        self.sprite.set_alpha(127)

    def intersect(self, player):
        was = self.hp.value
        super().intersect(player)
        if not was and self.hp.value == 1:
            self.sprite.set_alpha(255)
        if self.hp.is_full():
            return self.building
        else:
            return self

    def paint(self, surface, shift):
        if not self.alive:
            return
        surface.blit(Game.Game().hexagons[GRASS], self.world_position + shift)
        surface.blit(self.sprite, self.world_position + shift)


class Source(Hexagon):

    def __init__(self, source_type, hexagon=None):
        super().__init__(RESOURCE, hexagon)
        self.source_type = source_type
        self.progress = ProgressBar(TRADE[source_type], self.world_position)
        self.last_player = None
        self.set_sprite(load_image(SPRITES_PATHS[source_type]))

    def increase(self, player):
        if (self.last_player != player) and not self.progress.value:
            self.progress += 1
            self.last_player = player
        elif self.last_player == player:
            self.progress += 1
        else:
            self.progress -= 1
        if self.progress.is_full():
            # __main__.get_game().get_current_session().spawn_recource(*self.hexagon)
            self.progress.set_value(0)
            self.last_player = None

    def paint(self, surface, shift):
        super().paint(surface, shift)
        if self.progress.value:
            self.progress.flip(surface, shift)


class UnitSpawn(Building):

    def __init__(self, player, building_type, hexagon=None):
        super().__init__(player, building_type, hexagon)
        self.alpha = 0
        self.path = None

    def tick(self):
        self.alpha += 1
        if (self.alpha / FPS) == \
                Game.Game().session.attributes.spawn_rate:
            if self.path:
                self.path.spawn_mob()
            self.alpha = 0

    def paint(self, surface, shift, show_path=False):
        super().paint(surface, shift)
        self.path.paint(surface, shift, show_path)


class Road(Building):

    def __init__(self, player, hexagon=None):
        super().__init__(player, ROAD, hexagon)
        self.set_sprite(load_image(SPRITES_PATHS[ROAD]))

    def on_click(self, button):
        pass


class Castle(UnitSpawn):

    def __init__(self, player, hexagon=None):
        super().__init__(player, CASTLE, hexagon)
        path = deque()
        path.append(hexagon)
        self.path = Path(path, player=self.player)
        self.set_sprite(load_image(SPRITES_PATHS[CASTLE]))

    def add_path_point(self, hexagon):
        self.path.add_point(hexagon)

    def tick(self):
        super().tick()
        self.path.tick()


class Storage(Building):

    def __init__(self, player, capacity, type, hexagon=None):
        super().__init__(player, STORAGE, hexagon)
        self.capacity = capacity
        self.type = type
        self.set_sprite(load_image(SPRITES_PATHS[STORAGE]))


class Canteen(Building):

    def __init__(self, player, hexagon=None):
        super().__init__(player, CANTEEN, hexagon)
        self.set_sprite(load_image(SPRITES_PATHS[CANTEEN]))


class Path(list):

    def __init__(self, points=deque(), player=0, limit=10):
        super().__init__()
        self.points = points
        self.limit = limit
        self.player = player

    def spawn_mob(self):
        if len(self) < self.limit:
            self.append(Man(1, 1, self.points.copy(), player=self.player))

    def add_point(self, point):
        self.points.append(point)
        for man in self:
            man.path.append(point)

    def remove_point(self, point):
        # Заменить на удаление точки
        points = []
        for man in self.copy():
            if man.get_hexagon() in points:
                man.kill()
                self.remove(man)

    def tick(self):
        for man in self.copy():
            if not man.tick():
                self.remove(man)

    def __bool__(self):
        return len(self.points) > 1

    def paint(self, surface, shift, show=False, selected=False):
        if show:
            for ind, i in enumerate(self.points):
                if selected:
                    pygame.draw.circle(surface, (122, 122, 0), Game.get_hexagon_pos(*i, shift), 7)
                pygame.draw.circle(surface, (0, 0, 0), Game.get_hexagon_pos(*i, shift), 5)
            if selected and len(self.points) > 1:
                pygame.draw.lines(surface, (122, 122, 0), False,
                                  list(map(lambda x: Game.get_hexagon_pos(*i, shift), self.points)), 6)
            if len(self.points) > 1:
                if selected:
                    pygame.draw.lines(surface, (122, 122, 0), False, list(map(lambda x: Game.get_hexagon_pos(*x, shift), self.points)), 4)
                pygame.draw.lines(surface, (0, 0, 0), False,
                                  list(map(lambda x: Game.get_hexagon_pos(*x, shift), self.points)), 4)
        for man in self:
            man.paint(surface, shift)

    def copy(self):
        return Path(self.points.copy(), self.player, self.limit)

    def __copy__(self):
        return Path(self.points.copy(), self.player, self.limit)


class Man(Object):

    def __init__(self, hp, dmg, path, player=0):
        self.start_hexagon = path.popleft()
        super().__init__(hexagon=self.start_hexagon, player=player)
        self.life_time = Game.Game().session.attributes.life_time
        self.hp = hp
        self.dmg = dmg
        self.path = path
        self.start = self.world_position
        self.alpha = 0
        self.alive = True

    def set_hexagon(self, hexagon):
        self.hexagon = hexagon
        game = Game.Game()
        self.world_position = pygame.Vector2(
            game.center.x + hexagon[0] * STANDARD_WIDTH // 2 + 32,
            game.center.y + hexagon[
                1] * STANDARD_HEIGHT + 32)

    def kill(self):
        self.alive = False

    def move(self):
        end = self.path[0]
        game = Game.Game()
        end = pygame.Vector2(
            game.center.x + end[0] * STANDARD_WIDTH // 2 + 32,
            game.center.y + end[1] * STANDARD_HEIGHT + 32)
        self.set_world_position(self.start.lerp(end, self.alpha))
        if self.alpha == 1:
            self.start_hexagon = self.path.popleft()
            self.start = end
            self.alpha = 0
            if game.session.field.intersect_hexagon(self.start_hexagon, self.player):
                self.kill()

    def tick(self):
        if not self.alive:
            return False
        game = Game.Game()
        now = game.session.field.get_hexagon(
                *self.hexagon)
        if CANTEEN in map(lambda x: x.building_type, filter(lambda x: Building in x.__class__.__bases__, tuple(now.get_neighbors().values()) + (now,))):
            self.life_time = game.session.attributes.life_time
        else:
            self.life_time -= RATE
        if self.life_time < 0:
            self.kill()
            return False
        elif self.path:
            self.increase_alpha(1 / FPS)
            self.move()
        return True

    def increase_alpha(self, delta):
        self.alpha = min(1, delta / max(abs(self.start_hexagon[0] - self.path[0][0]) // 2,
                                        abs(self.start_hexagon[1] - self.path[0][1])) + self.alpha)

    def paint(self, surface, shift):
        if self.alive:
            return pygame.draw.circle(surface, PLAYER_COLORS[Game.Game().session.player], self.world_position + shift,
                                      self.life_time * 2)

    def get_hexagon(self):
        return Game.get_hexagon_by_world_pos(self.world_position)


class Deliveryman(Man):

    def __init__(self, hp, life_time, start):
        super().__init__(hp, 0, life_time, deque())
        self.start = start


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
    elif hex_type == STORAGE:
        return Castle(player, hexagon)
    elif hex_type == WATER:
        n = Hexagon(hex_type, hexagon)
        n.set_sprite(load_image(SPRITES_PATHS[hex_type]))
        return n
    elif hex_type == GRASS:
        return Hexagon(hex_type, hexagon)
    elif hex_type == PROJECT:
        return Project(player, hexagon, create_hexagon(player, hexagon, *args),
                       RESOURCES_FOR_BUILD[args[0]][2])
    elif hex_type == CANTEEN:
        return Canteen(player, hexagon)

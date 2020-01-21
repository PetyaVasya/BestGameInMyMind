from collections import deque

from Tools import *
import __main__


class Object:

    def __init__(self, hexagon=None):
        self.sprite = None
        self.hexagon = None
        if hexagon:
            self.set_hexagon(hexagon)
        else:
            self.world_position = pygame.Vector2(0, 0)

    def set_hexagon(self, hexagon):
        self.hexagon = hexagon
        self.world_position = pygame.Vector2(
            __main__.get_game().center_x + hexagon[0] * STANDARD_WIDTH // 2,
            __main__.get_game().center_y + hexagon[
                1] * STANDARD_HEIGHT)

    def set_world_position(self, vector2):
        self.world_position = vector2
        self.hexagon = get_hexagon_by_world_pos(self.world_position)

    def set_sprite(self, sprite):
        if sprite:
            self.sprite = sprite
        else:
            self.sprite = None


class Hexagon(Object):

    def __init__(self, type, hexagon=None):
        super().__init__(hexagon)
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
                 self.hexagon[1] + y): __main__.get_game().get_current_fight().field.get_hexagon(
                    self.hexagon[0] + x // (abs(y) + 1), self.hexagon[1] + y) for x in
                range(-2, 3, 2) for y in
                range(-1, 2) if (x != 0) and not (x == y == 0)}
        else:
            return {}


class Building(Hexagon):

    def __init__(self, player, building_type, hexagon=None):
        super().__init__(BUILDING, hexagon)
        self.player = player
        self.level = 1
        self.building_type = building_type
        self.set_sprite(load_image(SPRITES_PATHS[building_type]))

    def destroy(self):
        pass

    def left_click(self):
        __main__.get_game().get_current_fight().set_selected(self)
        # self.selected = True

    # def upgrade(self):


class UnitSpawn(Building):

    def __init__(self, player, building_type, hexagon=None):
        super().__init__(player, building_type, hexagon)
        self.alpha = 0
        self.path = None

    def tick(self):
        self.alpha += 1
        if (self.alpha / FPS) == \
                __main__.get_game().get_current_fight().get_attributes().spawn_rate:
            if self.path:
                self.path.spawn_mob()
                print("SPAWNED")
            self.alpha = 0

    def paint(self, surface, shift):
        super().paint(surface, shift)
        self.path.paint(surface, shift)


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
        self.path = Path(path)
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


class Path(list):

    def __init__(self, points, limit=10):
        super().__init__()
        self.points = points
        self.limit = limit

    def spawn_mob(self):
        if len(self) < self.limit:
            self.append(Man(1, 1, self.points.copy()))

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

    def paint(self, surface, shift):
        for man in self:
            man.paint(surface, shift)


class Man(Object):

    def __init__(self, hp, dmg, path):
        self.start_hexagon = path.popleft()
        super().__init__(self.start_hexagon)
        self.life_time = __main__.get_game().get_current_fight().get_attributes().life_time
        self.hp = hp
        self.dmg = dmg
        self.path = path
        self.start = self.world_position
        self.alpha = 0

    def set_hexagon(self, hexagon):
        self.hexagon = hexagon
        self.world_position = pygame.Vector2(
            __main__.get_game().center_x + hexagon[0] * STANDARD_WIDTH // 2 + 32,
            __main__.get_game().center_y + hexagon[
                1] * STANDARD_HEIGHT + 32)

    def kill(self):
        pass

    def move(self):
        end = self.path[0]
        end = pygame.Vector2(
            __main__.get_game().center_x + end[0] * STANDARD_WIDTH // 2 + 32,
            __main__.get_game().center_y + end[1] * STANDARD_HEIGHT + 32)
        self.set_world_position(self.start.lerp(end, self.alpha))
        if self.alpha == 1:
            self.start_hexagon = self.path.popleft()
            self.start = end
            self.alpha = 0

    def tick(self):
        if CANTEEN in __main__.get_game().get_current_fight().field.get_hexagon(
                *self.hexagon).get_neighbors().values():
            self.life_time = __main__.get_game().life_time
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
        return pygame.draw.circle(surface, (0, 0, 0), self.world_position + shift,
                                  self.life_time * 2)

    def get_hexagon(self):
        return get_hexagon_by_world_pos(self.world_position)


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
        return Castle(player, hexagon)
    elif hex_type == MINE:
        return Castle(player, hexagon)
    elif hex_type == STORAGE:
        return Castle(player, hexagon)
    elif hex_type == WATER:
        return Hexagon(hexagon)
    elif hex_type == GRASS:
        return Hexagon(hexagon)

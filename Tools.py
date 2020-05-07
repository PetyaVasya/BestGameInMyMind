import re
from math import radians, sin, cos, sqrt
from os import listdir
from os.path import isfile, join

import pygame
# from shapely.geometry import Point
# from shapely.geometry.polygon import Polygon
from constants import *


# from Game import Game


def load_image(name, colorkey=None, scale=(STANDARD_WIDTH, STANDARD_WIDTH)):
    return pygame.transform.scale(pygame.image.load(name).convert_alpha(),
                                  scale)


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [atoi(c) for c in re.split(r'(\d+)', text)]


def load_image_set(name, scale=None):
    if scale:
        return [pygame.transform.scale(pygame.image.load(join(name, f)).convert_alpha(), scale) for
                f in
                sorted(listdir(name), key=natural_keys) if
                isfile(join(name, f))]
    return [pygame.image.load(join(name, f)).convert_alpha() for f in
            sorted(listdir(name), key=natural_keys) if
            isfile(join(name, f))]


def euclidean(point1, point2):
    return sqrt((point2.x - point1.x) ** 2 + (point2.y - point1.y) ** 2)


# stolen from https://medium.com/@nicholas.w.swift/easy-a-star-pathfinding-7e6689c7f7b2
# with some fixes and changes

class Node:
    """A node class for A* Pathfinding"""

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position


def astar(maze, start, end):
    """Returns a list of tuples as a path from the given start to the given end in the given maze"""

    # Create start and end node
    start_node = Node(None, start)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end)
    end_node.g = end_node.h = end_node.f = 0

    # Initialize both open and closed list
    open_list = []
    closed_list = []

    # Add the start node
    open_list.append(start_node)

    # Loop until you find the end
    while len(open_list) > 0:
        # Get the current node
        current_node = open_list[0]
        current_index = 0
        for index, item in enumerate(open_list):
            if item.f < current_node.f:
                current_node = item
                current_index = index
        # Pop current off open list, add to closed list
        open_list.pop(current_index)
        closed_list.append(current_node)

        # Found the goal
        if current_node == end_node:
            path = []
            current = current_node
            while current is not None:
                path.append(current.position)
                current = current.parent
            return path[::-1]  # Return reversed path

        # Generate children
        children = []
        for new_position in [(-2, 0), (-1, -1), (1, -1), (2, 0), (1, 1),
                             (-1, 1)]:  # Adjacent squares

            # Get node position
            node_position = (
                current_node.position[0] + new_position[0],
                current_node.position[1] + new_position[1])

            # Make sure within range
            if node_position[0] > (len(maze) - 1) or node_position[0] < 0 or node_position[1] > (
                    len(maze[len(maze) - 1]) - 1) or node_position[1] < 0:
                continue

            # Make sure walkable terrain
            if maze[node_position[0]][node_position[1]] != 0:
                continue

            # Create new node
            new_node = Node(current_node, node_position)

            # Append
            children.append(new_node)

        counter = 0
        # Loop through children
        for child in children:

            # Child is on the closed list
            skip = False
            for closed_child in closed_list:
                if child == closed_child:
                    skip = True
                    counter += 1
                    break
            if skip:
                continue

            # Create the f, g, and h values
            child.g = current_node.g + 1
            child.h = ((child.position[0] - end_node.position[0]) ** 2) + (
                    (child.position[1] - end_node.position[1]) ** 2)
            child.f = child.g + child.h

            # Child is already in the open list
            skip = False
            for open_node in open_list:
                if child == open_node and child.g > open_node.g:
                    skip = True
                    break
            if skip:
                continue

            # Add the child to the open list
            open_list.append(child)
        if counter == 6:
            path = []
            current = current_node
            while current is not None:
                path.append(current.position)
                current = current.parent
            return path[::-1]


class PositionTarget:

    def __init__(self, start: pygame.Vector2, end: pygame.Vector2, speed: float):
        self.start = start
        self.end = end
        self.speed = speed
        self.alpha = 0
        self.distance = self.start.distance_to(self.end)
        if not self.distance:
            self.alpha = 1

    def tick(self, delta):
        if self.alpha == 1:
            return self.end
        self.alpha = min(self.alpha + self.speed * delta / self.distance, 1)
        return self.start.lerp(self.end, self.alpha)

    def is_reached(self):
        return self.alpha == 1

    def current(self):
        return self.start.lerp(self.end, self.alpha)

    def get_time_left(self):
        return (self.distance - self.distance * self.alpha) / self.speed


class PropertyTarget:

    def __init__(self, setter, start, end, duration=1):
        self.setter = setter
        self.start = start
        self.distance = end - start
        self.duration = duration
        self.alpha = 0

    def tick(self, delta):
        self.alpha += delta / self.duration
        self.alpha = min(1, self.alpha)
        self.setter(self.start + self.alpha * self.distance)
        return self.is_end()

    def is_end(self):
        return self.alpha == 1

    def __hash__(self):
        return hash(str(self.duration) + str(hash(self.setter)) + str(self.start))


class ActionAfter:

    def __init__(self, action, time):
        self.time = time
        self.action = action

    def tick(self, delta):
        self.time = max(0, self.time - delta)
        if self.is_ended():
            self.action()
            return True
        return False

    def is_ended(self):
        return not self.time


class Animation:

    def __init__(self):
        self.active = set()
        self._a = 0

    def change_value(self, setter, start, end, duration=1):
        """
        variable must be function
        :param setter:
        :param start:
        :param end:
        :param duration:
        :return:
        """
        self.active.add(PropertyTarget(setter, start, end, duration))

    def move(self, end, duration):
        self.active.add(PropertyTarget(self.set_world_position, self.world_position, end, duration))

    def rotate(self, angle, duration):
        def setter(x):
            self.rotation = x

        self.active.add(PropertyTarget(setter, self.rotation, angle, duration))

    def kill_after(self, duration):
        def new():
            self.alive = False

        self.active.add(ActionAfter(new, duration))

    def tick(self, delta):
        new = set()
        for a in self.active:
            if not a.tick(delta):
                new.add(a)
        self.active = new

"""Battlecode bot with BFS + return-path conveyor building"""

import random
from collections import deque

from cambc import Controller, Direction, EntityType, Position

# IMPORTANT: manually define directions (engine is not iterable)
DIRECTIONS = [
    Direction.NORTH,
    Direction.SOUTH,
    Direction.EAST,
    Direction.WEST,
    
]


class Player:
    def __init__(self) -> None:
        self.num_spawned = 0
        self.core_pos = None

        # path system
        self.current_path = []
        self.path_index = 0
        self.returning = False

    def run(self, ct: Controller) -> None:
        self.delegate_behaviour(ct)

    def delegate_behaviour(self, ct: Controller) -> None:
        etype = ct.get_entity_type()

        if etype == EntityType.CORE:
            self.execute_core_behaviour(ct)
        elif etype == EntityType.BUILDER_BOT:
            self.execute_builder_bot_behaviour(ct)

    # ================= CORE =================
    def execute_core_behaviour(self, ct: Controller) -> None:
        self.core_pos = ct.get_position()

        if self.num_spawned < 3:
            pos = ct.get_position()

            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    target = Position(pos.x + dx, pos.y + dy)

                    if ct.can_spawn(target):
                        ct.spawn_builder(target)
                        self.num_spawned += 1
                        return

    # ================= BUILDER =================
    def execute_builder_bot_behaviour(self, ct: Controller) -> None:
        my_pos = ct.get_position()

        # ================= RETURN MODE =================
        if self.returning:
            if self.path_index < len(self.current_path):
                next_step = self.current_path[self.path_index]
                move_dir = self.get_direction_to(my_pos, next_step)

                if move_dir and ct.can_move(move_dir):
                    # build conveyor on current tile BEFORE moving
                    if ct.can_build_conveyor(my_pos):
                        ct.build_conveyor(my_pos)

                    ct.move(move_dir)
                    self.path_index += 1
                    return
            else:
                # finished return
                self.returning = False
                self.current_path = []
                self.path_index = 0
                return

        # ================= BUILD HARVESTER =================
        for d in DIRECTIONS:
            check_pos = my_pos.add(d)
            if ct.can_build_harvester(check_pos):
                ct.build_harvester(check_pos)

                # reverse path to go back to core
                if self.current_path:
                    self.current_path.reverse()
                    self.path_index = 0
                    self.returning = True

                return

        # ================= FIND PATH =================
        if not self.current_path:
            self.current_path = self.bfs_to_ore(ct, max_radius=10) or []
            self.path_index = 0

        # ================= FOLLOW PATH =================
        if self.current_path and self.path_index < len(self.current_path):
            next_step = self.current_path[self.path_index]
            move_dir = self.get_direction_to(my_pos, next_step)
        else:
            move_dir = random.choice(DIRECTIONS)

        if move_dir is None:
            move_dir = random.choice(DIRECTIONS)

        move_pos = my_pos.add(move_dir)
        if (move_dir == Direction.EAST):
            conveyor_dir = Direction.WEST
        elif (move_dir == Direction.WEST):
            conveyor_dir = Direction.EAST
        elif move_dir == Direction.NORTH:
            conveyor_dir = Direction.SOUTH
        else:
            conveyor_dir = Direction.NORTH

        # build road before moving
        if ct.can_build_conveyor(move_pos,conveyor_dir):
            ct.build_conveyor(move_pos,conveyor_dir)

        if ct.can_move(move_dir):
            ct.move(move_dir)
            self.path_index += 1
       

    # ================= BFS =================
    def bfs_to_ore(self, ct: Controller, max_radius=10):
        start = ct.get_position()

        queue = deque([start])
        visited = {(start.x, start.y)}
        parent = {}

        while queue:
            current = queue.popleft()

            # found ore
            if hasattr(ct, "is_ore") and ct.is_ore(current):
                return self.reconstruct_path(parent, start, current)

            if abs(current.x - start.x) + abs(current.y - start.y) > max_radius:
                continue

            for d in DIRECTIONS:
                nxt = current.add(d)
                key = (nxt.x, nxt.y)

                if key in visited:
                    continue

                # only explore usable tiles
                if not ct.can_build_road(nxt) and not ct.can_move(d):
                    continue

                visited.add(key)
                parent[key] = (current.x, current.y)
                queue.append(nxt)

        return None

    def reconstruct_path(self, parent, start, end):
        path = []
        curr = (end.x, end.y)

        while curr != (start.x, start.y):
            path.append(Position(curr[0], curr[1]))
            curr = parent[curr]

        path.reverse()
        return path

    # ================= HELPERS =================
    def get_direction_to(self, start: Position, nxt: Position):
        dx = nxt.x - start.x
        dy = nxt.y - start.y

        for d in DIRECTIONS:
            if d.dx == dx and d.dy == dy:
                return d

        return None
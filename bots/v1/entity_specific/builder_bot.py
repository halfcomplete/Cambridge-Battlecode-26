from collections import deque
import random, math
from constants import DIRECTIONS

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

"""
How we will use markers
    - Builder bots will place a marker everytime they move to a new tile
    - The marker's value (32-bit integer) will document the tile types in the surrounding 
"""

class BuilderBotState:
    """
    Class to represent the state of a builder bot entity, which can be used to make decisions in its behaviour logic.
    """
    def __init__(self):
        self.num_spawned = 0
        self.returning = False
        self.current_path = []
        self.path_index = 0

        self.known_map = {} # maps (x, y) to (Environment, int) where Environment is the type of the tile and int is the round number when we last saw this tile


def execute_behaviour(ct: Controller, state: BuilderBotState) -> None:
    """
    This function is the main entry point for main.py to run the builder bot's behaviour logic.
    """
    my_pos = ct.get_position()

    # ================= RETURN MODE =================
    if state.returning:
        if state.path_index < len(state.current_path):
            next_step = state.current_path[state.path_index]
            move_dir = state.get_direction_to(my_pos, next_step)

            if move_dir and ct.can_move(move_dir):
                # build conveyor on current tile BEFORE moving
                if ct.can_build_conveyor(my_pos):
                    ct.build_conveyor(my_pos)

                ct.move(move_dir)
                state.path_index += 1
                return
        else:
            # finished return
            state.returning = False
            state.current_path = []
            state.path_index = 0
            return

    # ================= BUILD HARVESTER =================
    for d in DIRECTIONS:
        check_pos = my_pos.add(d)
        if ct.can_build_harvester(check_pos):
            ct.build_harvester(check_pos)

            # reverse path to go back to core
            if state.current_path:
                state.current_path.reverse()
                state.path_index = 0
                state.returning = True

            return

    # ================= FIND PATH =================
    if not state.current_path:
        state.current_path = state.bfs_to_ore(ct, max_radius=10) or []
        state.path_index = 0

    # ================= FOLLOW PATH =================
    if state.current_path and state.path_index < len(state.current_path):
        next_step = state.current_path[state.path_index]
        move_dir = state.get_direction_to(my_pos, next_step)
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
        state.path_index += 1
    

# ================= BFS =================
def bfs_to_ore(state, ct: Controller, max_radius=10):
    start = ct.get_position()

    queue = deque([start])
    visited = {(start.x, start.y)}
    parent = {}

    while queue:
        current = queue.popleft()

        # found ore
        # if ct.get_tile_env(current) in (Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
        #     return self.reconstruct_path(parent, start, current)

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

# def reconstruct_path(self, parent, start, end):
#     path = []
#     curr = (end.x, end.y)

#     while curr != (start.x, start.y):
#         path.append(Position(curr[0], curr[1]))
#         curr = parent[curr]

#     path.reverse()
#     return path

def determine_tile_to_move_to() -> Position:
    ...
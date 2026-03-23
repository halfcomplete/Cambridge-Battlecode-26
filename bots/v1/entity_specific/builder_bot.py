import heapq
import random

from constants import DIRECTIONS
import logic_utils

from cambc import Controller, Direction, EntityType, Environment, Position  # type: ignore


class BuilderBotState:
    def __init__(self):
        self.core_position = Position(-1, -1)
        self.known_map = {}


# ================= MAIN =================

def execute_behaviour(ct: Controller, state: BuilderBotState) -> None:
    my_pos = ct.get_position()

    _update_known_map(ct, state)

    if state.core_position == Position(-1, -1):
        _try_cache_core_position(ct, state)

    # ===== FIND ORE =====
    visible_ore = _get_visible_ore_tiles(ct)

    target_tile = None

    if visible_ore:
        ore = min(visible_ore, key=lambda p: my_pos.distance_squared(p))

        # build immediately if possible
        if ct.can_build_harvester(ore):
            ct.build_harvester(ore)
            return

        # move to adjacent tile instead
        target_tile = _get_adjacent_build_tile(ct, ore)

    # ===== EXPLORE =====
    if target_tile is None:
        target_tile = _pick_explore_target(ct, state, my_pos)

    if target_tile is None:
        return

    # ===== PATHFIND =====
    move_dir = _a_star_next_direction(ct, my_pos, target_tile)

    if move_dir is None:
        return

    next_pos = my_pos.add(move_dir)
    back_dir = next_pos.direction_to(my_pos)

    # ===== BUILD IF BLOCKED =====
    if not ct.is_tile_passable(next_pos):
        if ct.can_build_conveyor(next_pos, back_dir):
            ct.build_conveyor(next_pos, back_dir)
            return

    # ===== MOVE =====
    if ct.get_move_cooldown() == 0 and ct.can_move(move_dir):
        ct.move(move_dir)


# ================= A* =================

def _a_star_next_direction(ct: Controller, start: Position, goal: Position) -> Direction | None:
    if start == goal:
        return None

    open_heap = []
    heapq.heappush(open_heap, (0, 0, start))

    came_from = {}
    g_score = {start: 0}
    visited = set()
    tie = 0

    while open_heap:
        _, _, current = heapq.heappop(open_heap)

        if current in visited:
            continue
        visited.add(current)

        if current == goal:
            return _reconstruct_next_direction(start, goal, came_from)

        for d in DIRECTIONS:
            neighbor = current.add(d)

            if not logic_utils.is_position_in_bounds(ct, neighbor):
                continue
            if neighbor in visited:
                continue

            # ONLY walkable tiles
            if not ct.is_tile_passable(neighbor) and neighbor != goal:
                continue

            tentative_g = g_score[current] + 1

            if tentative_g >= g_score.get(neighbor, float("inf")):
                continue

            came_from[neighbor] = current
            g_score[neighbor] = tentative_g

            tie += 1
            h = logic_utils.chebyshev_distance(neighbor, goal)
            f = tentative_g + h

            heapq.heappush(open_heap, (f, tie, neighbor))

    return None


def _reconstruct_next_direction(start: Position, goal: Position, came_from):
    if goal not in came_from:
        return None

    node = goal
    while node in came_from and came_from[node] != start:
        node = came_from[node]

    return start.direction_to(node)


# ================= TARGETING =================

def _get_adjacent_build_tile(ct: Controller, ore_pos: Position) -> Position | None:
    for d in DIRECTIONS:
        adj = ore_pos.add(d)
        if logic_utils.is_position_in_bounds(ct, adj) and ct.is_tile_passable(adj):
            return adj
    return None


def _get_visible_ore_tiles(ct: Controller):
    ore_tiles = []
    for tile in ct.get_nearby_tiles():
        env = ct.get_tile_env(tile)
        if env in (Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
            ore_tiles.append(tile)
    return ore_tiles


# ================= EXPLORATION =================

def _pick_explore_target(ct: Controller, state: BuilderBotState, my_pos: Position):
    candidates = []

    for d in DIRECTIONS:
        tile = my_pos.add(d)
        if not logic_utils.is_position_in_bounds(ct, tile):
            continue
        if ct.is_tile_passable(tile):
            candidates.append(tile)

    if not candidates:
        return None

    # move away from core
    if state.core_position != Position(-1, -1):
        return max(candidates, key=lambda p: p.distance_squared(state.core_position))

    return random.choice(candidates)


# ================= UTIL =================

def _update_known_map(ct: Controller, state: BuilderBotState):
    round_num = ct.get_current_round()
    for tile in ct.get_nearby_tiles():
        state.known_map[(tile.x, tile.y)] = (ct.get_tile_env(tile), round_num)


def _try_cache_core_position(ct: Controller, state: BuilderBotState):
    my_team = ct.get_team()
    for bid in ct.get_nearby_buildings():
        if ct.get_entity_type(bid) == EntityType.CORE and ct.get_team(bid) == my_team:
            state.core_position = ct.get_position(bid)
            return
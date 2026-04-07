import heapq
import random

from constants import DIRECTIONS
import logic_utils
from debug_utils import print_debug_msg

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
        return []

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
            return _reconstruct_path(start, goal, came_from)

        for d in DIRECTIONS:
            neighbor = current.add(d)

            if not logic_utils.is_position_in_bounds(ct, neighbor):
                continue
            if not ct.is_in_vision(neighbor):
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

    nodes = [goal]
    node = goal
    while node in came_from and came_from[node] != start:
        node = came_from[node]
        nodes.append(node)

    nodes.reverse()

    path: list[Direction] = []
    for idx in range(1, len(nodes)):
        path.append(nodes[idx - 1].direction_to(nodes[idx]))

    return path


def _path_cost(ct: Controller, start: Position, path: list[Direction]) -> float:
    total = 0.0
    position = start
    for direction in path:
        position = position.add(direction)
        total += _get_tile_move_cost(ct, position, allow_goal=True)
    return total


def _try_move_with_infrastructure(
    ct: Controller,
    direction: Direction,
    build_strategy: str = "road",
    conveyor_direction: Direction | None = None,
    replace_road_only: bool = False,
) -> str:
    """
    Returns one of:
    - moved
    - detour_moved
    - cooldown
    - temporary_block
    - permanent_block
    """
    if ct.get_move_cooldown() > 0:
        return "cooldown"

    # If a diagonal target tile is currently unwalkable, use one-step cardinal detour.
    if _is_diagonal_direction(direction):
        detour = _choose_diagonal_detour(ct, direction, build_strategy)
        if detour is not None:
            detour_outcome = _try_move_with_infrastructure(
                ct,
                detour,
                build_strategy,
                conveyor_direction=conveyor_direction,
                replace_road_only=replace_road_only,
            )
            if detour_outcome in ("moved", "detour_moved"):
                return "detour_moved"

    my_pos = ct.get_position()
    next_pos = my_pos.add(direction)
    if not logic_utils.is_position_in_bounds(ct, next_pos):
        return "permanent_block"

    occupying_builder_id = ct.get_tile_builder_bot_id(next_pos)
    if occupying_builder_id is not None and occupying_builder_id != ct.get_id():
        return "temporary_block"

    # Return-mode special handling: replace road with conveyor before moving.
    if build_strategy == "conveyor":
        desired_dir = conveyor_direction if conveyor_direction is not None else direction
        desired_dir = _to_cardinal_direction(desired_dir, direction)

        if replace_road_only:
            building_id = ct.get_tile_building_id(next_pos)
            if building_id is not None and ct.get_entity_type(building_id) == EntityType.ROAD and ct.get_team(building_id) == ct.get_team():
                if ct.can_destroy(next_pos):
                    ct.destroy(next_pos)

                if ct.can_build_conveyor(next_pos, desired_dir):
                    ct.build_conveyor(next_pos, desired_dir)

    if ct.can_move(direction):
        ct.move(direction)
        return "moved"

    if build_strategy == "road":
        if ct.can_build_road(next_pos):
            ct.build_road(next_pos)
            if ct.can_move(direction):
                ct.move(direction)
                return "moved"

    if build_strategy == "conveyor":
        desired_dir = conveyor_direction if conveyor_direction is not None else direction
        desired_dir = _to_cardinal_direction(desired_dir, direction)
        if not _is_diagonal_direction(desired_dir):
            road_replaced = not replace_road_only
            if replace_road_only:
                building_id = ct.get_tile_building_id(next_pos)
                if building_id is not None and ct.get_entity_type(building_id) == EntityType.ROAD and ct.get_team(building_id) == ct.get_team():
                    if ct.can_destroy(next_pos):
                        ct.destroy(next_pos)
                        road_replaced = True

            if not road_replaced:
                if ct.can_move(direction):
                    ct.move(direction)
                    return "moved"
                return "temporary_block"

            if ct.can_build_conveyor(next_pos, desired_dir):
                ct.build_conveyor(next_pos, desired_dir)
                if ct.can_move(direction):
                    ct.move(direction)
                    return "moved"

    if _is_permanent_blocker(ct, next_pos):
        return "permanent_block"

    return "temporary_block"


def _is_permanent_blocker(ct: Controller, pos: Position) -> bool:
    """
    Returns True if the tile is blocked by something unlikely to clear soon.
    """
    if not ct.is_in_vision(pos):
        return False

    env = ct.get_tile_env(pos)
    if env == Environment.WALL:
        return True

    building_id = ct.get_tile_building_id(pos)
    if building_id is None:
        return False

    building_type = ct.get_entity_type(building_id)
    if building_type in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.ROAD):
        return False
    if building_type == EntityType.CORE and ct.get_team(building_id) == ct.get_team():
        return False

    return True


def _is_target_ore_valid(ct: Controller, ore_pos: Position) -> bool:
    """
    Ore target is valid when ore is still present and has no building on top.
    If target is currently out of vision, keep mission alive until verified.
    """
    if not ct.is_in_vision(ore_pos):
        return True

    env = ct.get_tile_env(ore_pos)
    if env not in (Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
        return False

    return ct.get_tile_building_id(ore_pos) is None


def _enter_exploring(state: BuilderBotState) -> None:
    """
    Clears ore mission state and enters EXPLORING.
    """
    state.mode = MODE_EXPLORING
    state.target_ore = None
    state.target_adjacent_tile = None
    state.return_goal_tile = None
    state.current_path = []
    state.return_path = []
    state.blocked_turns = 0


def _reset_after_harvester_build(state: BuilderBotState) -> None:
    """
    Transitions from ore-build phase into return-to-core conveyor phase.
    """
    state.mode = MODE_RETURNING_TO_CORE
    state.target_ore = None
    state.target_adjacent_tile = None
    state.current_path = []
    state.return_goal_tile = None
    state.return_path = []
    state.blocked_turns = 0


def _reset_after_return_complete(state: BuilderBotState) -> None:
    """
    Clears mission state after finishing return-to-core routing.
    """
    state.mode = MODE_IDLE
    state.return_goal_tile = None
    state.return_path = []
    state.blocked_turns = 0


def _draw_intended_move(ct: Controller, direction: Direction, r: int, g: int, b: int) -> None:
    """
    Draws short line showing immediate intended movement direction.
    """
    my_pos = ct.get_position()
    target_pos = my_pos.add(direction)
    if logic_utils.is_position_in_bounds(ct, target_pos):
        ct.draw_indicator_line(my_pos, target_pos, r, g, b)


def _draw_target_line(ct: Controller, target: Position | None, r: int, g: int, b: int) -> None:
    """
    Draws line from bot to current long-term target when visible.
    """
    if target is None:
        return
    if not logic_utils.is_position_in_bounds(ct, target):
        return
    if not ct.is_in_vision(target):
        return

    my_pos = ct.get_position()
    ct.draw_indicator_line(my_pos, target, r, g, b)


def _is_diagonal_direction(direction: Direction) -> bool:
    dx, dy = direction.delta()
    return dx != 0 and dy != 0


def _choose_diagonal_detour(ct: Controller, diagonal_direction: Direction, build_strategy: str = "road") -> Direction | None:
    """
    For a blocked diagonal attempt, choose one cardinal one-step detour.

    Preference:
    1. Immediately movable cardinal step.
    2. Cardinal step where we can place infrastructure and then move.
    """
    dx, dy = diagonal_direction.delta()
    cardinal_candidates = []

    if dx > 0:
        cardinal_candidates.append(Direction.EAST)
    elif dx < 0:
        cardinal_candidates.append(Direction.WEST)

    if dy > 0:
        cardinal_candidates.append(Direction.SOUTH)
    elif dy < 0:
        cardinal_candidates.append(Direction.NORTH)

    for candidate in cardinal_candidates:
        if ct.can_move(candidate):
            return candidate

    my_pos = ct.get_position()
    for candidate in cardinal_candidates:
        mid = my_pos.add(candidate)
        if not logic_utils.is_position_in_bounds(ct, mid):
            continue

        if build_strategy == "road":
            if ct.can_build_road(mid):
                return candidate
        else:
            back_direction = mid.direction_to(my_pos)
            if _is_diagonal_direction(back_direction):
                continue
            if ct.can_build_conveyor(mid, back_direction):
                return candidate

    return None


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
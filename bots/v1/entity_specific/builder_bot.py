import heapq
import random
from constants import DIRECTIONS, PASSABLE_TILE_COST, EMPTY_TILE_COST, IMPASSABLE_TILE_COST

import logic_utils

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
        
        self.core_position = Position(-1, -1) # initialize to an invalid position until we find the core


def execute_behaviour(ct: Controller, state: BuilderBotState) -> None:
    """
    This function is the main entry point for main.py to run the builder bot's behaviour logic.
    """
    
    """
    How pathfinding works:
    1. It will first check if there is any ore in sight. If there is, it will move towards the ore and build a harvester on it.
    2. If there isn't, it will move in a semi-random direction away from the core and any Claim-type markers.
    3. As the bot moves, it will build conveyors facing the direction it came from so that, if it finds ore, it can automatically route the harvester's output back to the core.
    4. Repeat.
    """
    my_pos = ct.get_position()
    _update_known_map(ct, state)

    if state.core_position == Position(-1, -1):
        # Cache our own core location once we see it.
        _try_cache_core_position(ct, state)

    # Detect ore in vision and build immediately if possible.
    visible_ore = _get_visible_ore_tiles(ct)
    target_ore = None
    if visible_ore:
        target_ore = min(visible_ore, key=lambda p: my_pos.distance_squared(p))
        if ct.can_build_harvester(target_ore):
            ct.build_harvester(target_ore)
            return

    # Pick where to move next (towards ore if seen, otherwise explore outwards from core).
    move_dir = None
    if target_ore is not None:
        move_dir = _a_star_next_direction(ct, my_pos, target_ore)

    # If we don't see any ore, pick a direction that leads us away from the core to explore new territory.
    if move_dir is None:
        explore_target = _pick_explore_target(ct, state, my_pos)
        if explore_target is not None:
            move_dir = _a_star_next_direction(ct, my_pos, explore_target)

    # If we don't see any ore 
    if move_dir is None:
        return

    next_pos = my_pos.add(move_dir)
    # Place a conveyor on the destination tile that points back to where we came from.
    # This creates a return path toward the core as we expand.
    back_dir = next_pos.direction_to(my_pos)

    if not ct.can_move(move_dir) and ct.can_build_conveyor(next_pos, back_dir):
        ct.build_conveyor(next_pos, back_dir)

    if ct.can_move(move_dir):
        ct.move(move_dir)


def _update_known_map(ct: Controller, state: BuilderBotState) -> None:
    """
    Updates the builder bot's known map with the tiles in vision. This allows the bot to remember where it has been and what it has seen, which can be useful for making decisions about where to move and where to build.
    
    TODO: Update the map when we see new markers as well
    """
    current_round = ct.get_current_round()
    for tile in ct.get_nearby_tiles():
        state.known_map[(tile.x, tile.y)] = (ct.get_tile_env(tile), current_round)


def _try_cache_core_position(ct: Controller, state: BuilderBotState) -> None:
    """
    Caches the position of the core in the builder bot's state if it is visible. This allows the bot to make informed decisions about where to explore.
    """
    my_team = ct.get_team()
    for building_id in ct.get_nearby_buildings():
        if ct.get_entity_type(building_id) == EntityType.CORE and ct.get_team(building_id) == my_team:
            state.core_position = ct.get_position(building_id)
            return


def _get_visible_ore_tiles(ct: Controller) -> list[Position]:
    """
    Returns a list of positions of ore tiles that are visible to the builder bot.
    """
    ore_tiles = []
    for tile in ct.get_nearby_tiles():
        env = ct.get_tile_env(tile)
        if env in (Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
            ore_tiles.append(tile)
    return ore_tiles


def _pick_explore_target(ct: Controller, state: BuilderBotState, my_pos: Position) -> Position | None:
    """
    Picks a target position to explore towards when we don't see any ore. This is done by looking at the 8 adjacent tiles and picking one that is navigable and leads us away from the core. If the core position is unknown, we will just pick a random navigable adjacent tile.
    """
    candidates = []
    # Get a list of candidates for where we can move to next.
    for d in DIRECTIONS:
        tile = my_pos.add(d)
        if not logic_utils.is_position_in_bounds(ct, tile):
            continue
        if _is_navigable_tile(ct, tile):
            candidates.append(tile)

    # If there are no candidates, return None.
    if not candidates:
        return None

    # Otherwise, pick the candidate that is furthest from the core to explore outwards
    # TODO: We can be smarter about this by also considering where we've already been (e.g. using the known map to prefer unexplored tiles) and by trying to maintain some level of path connectivity (e.g. not leaving isolated pockets of unexplored territory).
    # We could also use markers to document which tiles we've already explored and prefer tiles that are further from existing markers, to encourage spreading out more.
    if state.core_position != Position(-1, -1):
        return max(candidates, key=lambda p: p.distance_squared(state.core_position))

    return random.choice(candidates)


def _a_star_next_direction(ct: Controller, start: Position, goal: Position) -> Direction | None:
    """
    Uses the A* algorithm to find the next direction to move in to get from start to goal. Returns None if there is no path.
    """
    if start == goal:
        return None

    open_heap = []
    heapq.heappush(open_heap, (logic_utils.chebyshev_distance(start, goal), 0, start))

    # came_from maps a position to the position that we came from to get there. This is used to reconstruct the path once we reach the goal.
    came_from: dict[Position, Position] = {}
    # g_score maps a position to the cost of the cheapest path from start to that position that we have found so far. This is used to determine which paths to explore in the A* algorithm.
    g_score: dict[Position, float] = {start: 0}
    # already_explored is a set of positions that we have already explored and don't need to explore again. This is used to avoid cycles and redundant exploration in the A* algorithm.
    already_explored: set[Position] = set()
    tie_breaker = 0

    # Repeatedly explore the tile with the lowest f_score until we reach the goal or run out of tiles to explore.
    while open_heap:
        # Get the tile in the open heap with the lowest f_score. If there are multiple tiles with the same f_score, we use a tie breaker to ensure a consistent order of exploration.
        _, _, current = heapq.heappop(open_heap)
        if current in already_explored:
            continue

        if current == goal:
            return _reconstruct_next_direction(start, goal, came_from)

        already_explored.add(current)

        # For each of the 8 adjacent tiles, if it is navigable and we haven't already explored it, calculate the g_score of the path to get there through the current tile and add it to the open heap if it's better than any previously known path to that tile.
        for d in DIRECTIONS:
            neighbor = current.add(d)

            # Skip this neighbor if it's out of bounds, if we've already explored it, or if it's not navigable (e.g. a wall or a building). When checking if it's navigable, we allow the goal tile to be navigable even if it normally wouldn't be (e.g. if it's an ore tile), since we want to be able to path to the goal.
            if not logic_utils.is_position_in_bounds(ct, neighbor):
                continue
            if neighbor in already_explored:
                continue
            if not _is_navigable_tile(ct, neighbor, allow_goal=(neighbor == goal)):
                continue

            move_cost = _get_tile_move_cost(ct, neighbor, allow_goal=(neighbor == goal))
            if move_cost == IMPASSABLE_TILE_COST:
                continue

            tentative_g = g_score[current] + move_cost
            if tentative_g >= g_score.get(neighbor, float("inf")):
                continue

            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            # Add a tie breaker to ensure we explore all tiles in a consistent order
            tie_breaker += 1
            f_score = tentative_g + logic_utils.chebyshev_distance(neighbor, goal)
            heapq.heappush(open_heap, (f_score, tie_breaker, neighbor))

    return None


def _reconstruct_next_direction(start: Position, goal: Position, came_from: dict[Position, Position]) -> Direction | None:
    """
    Reconstructs the next direction to move in to get from start to goal using the came_from map generated by the A* algorithm. Returns None if there is no path.
    """
    if goal not in came_from:
        return None

    node = goal
    while came_from[node] != start:
        node = came_from[node]

    return start.direction_to(node)


def _get_tile_move_cost(ct: Controller, pos: Position, allow_goal: bool = False) -> float:
    """
    Returns the move cost of moving onto the given tile. If the tile is not navigable, returns IMPASSABLE_TILE_COST. If the tile is passable, returns PASSABLE_TILE_COST. If the tile is not passable but is still navigable, returns EMPTY_TILE_COST.
    """
    if not _is_navigable_tile(ct, pos, allow_goal=allow_goal):
        return IMPASSABLE_TILE_COST

    if ct.is_tile_passable(pos):
        return PASSABLE_TILE_COST

    return EMPTY_TILE_COST


def _is_navigable_tile(ct: Controller, pos: Position, allow_goal: bool = False) -> bool:
    """
    Returns whether the given tile is navigable for the builder bot, meaning that it can move onto it or build on it.
    """
    # Occupied by another builder bot means we cannot move there this turn and cannot build there.
    occupying_builder_id = ct.get_tile_builder_bot_id(pos)
    if occupying_builder_id is not None and occupying_builder_id != ct.get_id():
        return False

    env = ct.get_tile_env(pos)
    if env == Environment.WALL:
        return False

    building_id = ct.get_tile_building_id(pos)
    if building_id is not None:
        building_type = ct.get_entity_type(building_id)

        # Directly walkable: conveyors/roads of any team, and allied core.
        if building_type in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.ROAD):
            return True
        if building_type == EntityType.CORE and ct.get_team(building_id) == ct.get_team():
            return True

        # If this is the goal tile, allow pathing to it as long as it is explicitly buildable.
        if allow_goal and env in (Environment.EMPTY, Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
            return True

        return False

    # Buildable but not currently walkable tiles (will incur EMPTY_TILE_COST in A*).
    return env in (Environment.EMPTY, Environment.ORE_TITANIUM, Environment.ORE_AXIONITE)


import heapq
from constants import (
    DIRECTIONS,
    EMPTY_TILE_COST,
    EXPLORATION_BACKTRACK_PENALTY,
    EXPLORATION_MEMORY_WINDOW,
    EXPLORATION_RECENT_TILE_PENALTY,
    IMPASSABLE_TILE_COST,
    MARKER_KIND_CORE_SPAWN_LANE,
    MARKER_KIND_SHIFT,
    MARKER_KIND_VISIT,
    MARKER_PAYLOAD_MASK,
    MAX_TEMP_BLOCKED_TURNS,
    MODE_EXPLORING,
    MODE_IDLE,
    MODE_MOVING_TO_ORE,
    PASSABLE_TILE_COST,
    PATHFIND_NODE_BUDGET,
    VISIT_MARKER_FRESH_ROUNDS,
    VISIT_MARKER_MAX_PENALTY,
)

import logic_utils
from debug_utils import print_debug_msg

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position  # type: ignore


class BuilderBotState:
    """
    State for a builder bot.

    Important fields:
    - mode: high-level FSM mode.
    - target_ore: ore tile currently locked in MOVING_TO_ORE.
    - target_adjacent_tile: orthogonally-adjacent build tile chosen for target_ore.
    - current_path: queued list of movement directions.
    - blocked_turns: retry counter for temporary blockage.
    - known_map: maps (x, y) -> (Environment, last_seen_round).
    - recent_positions: short local memory used to break small exploration loops.
    - spiral_*: fields for square-spiral exploration that expands over time.
    - explore_fail_streak: consecutive exploration turns with no successful movement.
    """

    def __init__(self):
        self.num_spawned = 0

        self.mode = MODE_IDLE
        self.target_ore: Position | None = None
        self.target_adjacent_tile: Position | None = None
        self.current_path: list[Direction] = []
        self.blocked_turns = 0

        self.known_map: dict[tuple[int, int], tuple[Environment, int]] = {}
        self.recent_positions: list[tuple[int, int]] = []

        self.core_position = Position(-1, -1)

        # Spiral exploration state.
        self.spiral_initialized = False
        self.spiral_heading_idx = 0
        self.spiral_leg_length = 1
        self.spiral_steps_on_leg = 0
        self.spiral_legs_completed = 0

        # Exploration loop recovery state.
        self.explore_fail_streak = 0


def execute_behaviour(ct: Controller, state: BuilderBotState) -> None:
    """
    Main per-turn behaviour entry point.

    We write one visit marker each turn (when legal), update map memory, then:
    - continue MOVING_TO_ORE if locked, otherwise
    - acquire a visible ore target if possible, otherwise
    - explore.
    """
    my_pos = ct.get_position()
    _record_recent_position(state, my_pos)
    _try_place_visit_marker(ct)

    _update_known_map(ct, state)

    if state.core_position == Position(-1, -1):
        _try_cache_core_position(ct, state)

    if state.mode == MODE_MOVING_TO_ORE:
        _run_moving_to_ore(ct, state)
        return

    visible_ore = _get_visible_and_available_ore_tiles(ct)
    if visible_ore and _start_moving_to_ore(ct, state, visible_ore):
        _run_moving_to_ore(ct, state)
        return

    state.mode = MODE_EXPLORING
    _run_exploring(ct, state)


def _run_moving_to_ore(ct: Controller, state: BuilderBotState) -> None:
    """
    Executes one turn of MOVING_TO_ORE behaviour.
    """
    if state.target_ore is None or state.target_adjacent_tile is None:
        _enter_exploring(state)
        return

    if not _is_target_ore_valid(ct, state.target_ore):
        _enter_exploring(state)
        return

    my_pos = ct.get_position()
    if my_pos == state.target_adjacent_tile:
        if ct.can_build_harvester(state.target_ore):
            ct.build_harvester(state.target_ore)
            _reset_after_harvester_build(state)
            return

        if not _is_target_ore_valid(ct, state.target_ore):
            _enter_exploring(state)
        return

    if not state.current_path:
        if _replan_to_current_target(ct, state, my_pos):
            state.blocked_turns = 0
        else:
            state.blocked_turns += 1
            if state.blocked_turns > MAX_TEMP_BLOCKED_TURNS:
                _enter_exploring(state)
        return

    next_direction = state.current_path[0]
    _draw_intended_move(ct, next_direction, 255, 170, 0)
    _draw_target_line(ct, state.target_ore, 255, 80, 80)
    move_outcome = _try_move_with_optional_conveyor(ct, next_direction)
    print_debug_msg(
        ct,
        f"Trying to move {next_direction} towards ore at {state.target_ore}, outcome: {move_outcome}, blocked_turns: {state.blocked_turns}",
    )

    if move_outcome == "moved":
        state.current_path.pop(0)
        state.blocked_turns = 0
        return

    if move_outcome == "detour_moved":
        my_pos = ct.get_position()
        if _replan_to_current_target(ct, state, my_pos):
            state.blocked_turns = 0
        else:
            state.blocked_turns += 1
            if state.blocked_turns > MAX_TEMP_BLOCKED_TURNS:
                _enter_exploring(state)
        return

    if move_outcome == "cooldown":
        return

    if move_outcome == "temporary_block":
        if _replan_to_current_target(ct, state, my_pos):
            state.blocked_turns = 0
        else:
            state.blocked_turns += 1
            if state.blocked_turns > MAX_TEMP_BLOCKED_TURNS:
                _enter_exploring(state)
        return

    _enter_exploring(state)


def _run_exploring(ct: Controller, state: BuilderBotState) -> None:
    """
    Exploration uses a core-anchored outward square-spiral as primary behaviour.
    If enemy infrastructure is seen, we try to follow along it to continue expansion.
    Fallback local scoring is kept as a safety net for blocked terrain pockets.
    """
    my_pos = ct.get_position()

    _initialize_spiral_if_needed(ct, state, my_pos)

    enemy_pos = _get_nearest_enemy_infrastructure(ct, my_pos)
    if enemy_pos is not None:
        follow_direction = _get_enemy_follow_direction(ct, state, my_pos, enemy_pos)
        if follow_direction is not None:
            _draw_intended_move(ct, follow_direction, 40, 220, 120)
            follow_outcome = _try_move_with_optional_conveyor(ct, follow_direction)
            if follow_outcome in ("moved", "detour_moved"):
                state.explore_fail_streak = 0
                _advance_spiral_after_success(state)
                return
            if follow_outcome == "cooldown":
                return

    spiral_direction = _get_spiral_direction(state)
    _draw_intended_move(ct, spiral_direction, 80, 160, 255)
    move_outcome = _try_move_with_optional_conveyor(ct, spiral_direction)

    if move_outcome in ("moved", "detour_moved"):
        state.explore_fail_streak = 0
        _advance_spiral_after_success(state)
        return

    if move_outcome == "cooldown":
        return

    # Spiral step failed on terrain/blocking. Try rotating through remaining cardinal headings
    # so we can escape corners and continue expanding.
    for _ in range(3):
        _rotate_spiral_heading(state)
        candidate_direction = _get_spiral_direction(state)
        _draw_intended_move(ct, candidate_direction, 60, 200, 220)
        move_outcome = _try_move_with_optional_conveyor(ct, candidate_direction)
        if move_outcome in ("moved", "detour_moved"):
            state.explore_fail_streak = 0
            _advance_spiral_after_success(state)
            return
        if move_outcome == "cooldown":
            return

    loop_detected = _is_small_loop_pattern(state)
    fallback_direction = _pick_explore_escape_direction(ct, state, my_pos) if loop_detected else _pick_explore_direction(ct, state, my_pos)
    if fallback_direction is None:
        state.explore_fail_streak += 1
        _force_spiral_jump(state, ct)
        return

    _draw_intended_move(ct, fallback_direction, 120, 120, 255)
    fallback_outcome = _try_move_with_optional_conveyor(ct, fallback_direction)
    if fallback_outcome in ("moved", "detour_moved"):
        state.explore_fail_streak = 0
        _advance_spiral_after_success(state)
        return

    if fallback_outcome == "cooldown":
        return

    state.explore_fail_streak += 1
    _force_spiral_jump(state, ct)


def _start_moving_to_ore(ct: Controller, state: BuilderBotState, visible_ore: list[Position]) -> bool:
    """
    Chooses the best visible ore and plans path to an orthogonally-adjacent build tile.
    """
    my_pos = ct.get_position()
    best_choice = None

    for ore_pos in sorted(visible_ore, key=lambda p: my_pos.distance_squared(p)):
        goal_tile, path = _plan_path_to_ore_goal(ct, my_pos, ore_pos)
        if goal_tile is None or path is None:
            continue

        path_cost = _path_cost(ct, my_pos, path)
        candidate_key = (path_cost, len(path), my_pos.distance_squared(ore_pos))
        if best_choice is None or candidate_key < best_choice[0]:
            best_choice = (candidate_key, ore_pos, goal_tile, path)

    if best_choice is None:
        return False

    _, ore_pos, goal_tile, path = best_choice
    state.mode = MODE_MOVING_TO_ORE
    state.target_ore = ore_pos
    state.target_adjacent_tile = goal_tile
    state.current_path = path
    state.blocked_turns = 0
    return True


def _replan_to_current_target(ct: Controller, state: BuilderBotState, my_pos: Position) -> bool:
    """
    Replans to currently locked ore target.
    """
    if state.target_ore is None:
        return False

    goal_tile, path = _plan_path_to_ore_goal(ct, my_pos, state.target_ore)
    if goal_tile is None or path is None:
        return False

    state.target_adjacent_tile = goal_tile
    state.current_path = path
    return True


def _plan_path_to_ore_goal(ct: Controller, my_pos: Position, ore_pos: Position) -> tuple[Position | None, list[Direction] | None]:
    """
    Plans a path to an orthogonally adjacent tile to ore_pos.
    """
    if not _is_target_ore_valid(ct, ore_pos):
        return None, None

    orthogonal_directions = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
    candidates = []

    for direction in orthogonal_directions:
        adjacent = ore_pos.add(direction)
        if not logic_utils.is_position_in_bounds(ct, adjacent):
            continue
        if not ct.is_in_vision(adjacent):
            continue

        if _get_tile_move_cost(ct, adjacent, allow_goal=True) == IMPASSABLE_TILE_COST:
            continue

        if my_pos == adjacent:
            path = []
        else:
            path = _a_star_path(ct, my_pos, adjacent)
            if path is None:
                continue

        candidates.append((adjacent, path, _path_cost(ct, my_pos, path), len(path)))

    if not candidates:
        return None, None

    candidates.sort(key=lambda c: (c[2], c[3]))
    best_adjacent, best_path, _, _ = candidates[0]
    return best_adjacent, best_path


def _update_known_map(ct: Controller, state: BuilderBotState) -> None:
    """
    Updates known map with current vision.
    """
    current_round = ct.get_current_round()
    for tile in ct.get_nearby_tiles():
        state.known_map[(tile.x, tile.y)] = (ct.get_tile_env(tile), current_round)


def _try_cache_core_position(ct: Controller, state: BuilderBotState) -> None:
    """
    Caches allied core centre if visible.
    """
    my_team = ct.get_team()
    for building_id in ct.get_nearby_buildings():
        if ct.get_entity_type(building_id) == EntityType.CORE and ct.get_team(building_id) == my_team:
            state.core_position = ct.get_position(building_id)
            return


def _get_visible_and_available_ore_tiles(ct: Controller) -> list[Position]:
    """
    Returns visible ore tiles with no building currently on top.
    """
    ore_tiles = []
    for tile in ct.get_nearby_tiles():
        env = ct.get_tile_env(tile)
        if env in (Environment.ORE_TITANIUM, Environment.ORE_AXIONITE) and ct.get_tile_building_id(tile) is None:
            ore_tiles.append(tile)
    return ore_tiles


def _pick_explore_direction(ct: Controller, state: BuilderBotState, my_pos: Position) -> Direction | None:
    """
    Picks best local exploration direction using:
    - terrain/move cost
    - distance from core
    - stale/unknown map signal
    - recent local movement memory
    - fresh allied visit markers
    """
    candidates: list[tuple[float, Direction, Position]] = []
    current_round = ct.get_current_round()
    previous_pos = _get_previous_position(state)

    for direction in DIRECTIONS:
        tile = my_pos.add(direction)
        if not logic_utils.is_position_in_bounds(ct, tile):
            continue

        tile_cost = _get_tile_move_cost(ct, tile, allow_goal=True)
        if tile_cost == IMPASSABLE_TILE_COST:
            continue

        score = -5 * tile_cost
        if state.core_position != Position(-1, -1):
            score += 2 * tile.distance_squared(state.core_position)

        seen = state.known_map.get((tile.x, tile.y))
        if seen is None:
            score += 200
        else:
            _, seen_round = seen
            score += min(50, current_round - seen_round)

        if previous_pos is not None and tile == previous_pos:
            score -= EXPLORATION_BACKTRACK_PENALTY

        for idx in range(len(state.recent_positions) - 1, -1, -1):
            previous_xy = state.recent_positions[idx]
            if previous_xy == (tile.x, tile.y):
                recency_rank = len(state.recent_positions) - 1 - idx
                score -= max(10, EXPLORATION_RECENT_TILE_PENALTY - (12 * recency_rank))
                break

        visit_round = _read_visit_marker_round(ct, tile)
        if visit_round is not None:
            age = max(0, current_round - visit_round)
            if age < VISIT_MARKER_FRESH_ROUNDS:
                penalty = VISIT_MARKER_MAX_PENALTY - int((VISIT_MARKER_MAX_PENALTY * age) / VISIT_MARKER_FRESH_ROUNDS)
                score -= penalty

        candidates.append((score, direction, tile))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _initialize_spiral_if_needed(ct: Controller, state: BuilderBotState, my_pos: Position) -> None:
    """
    Initializes spiral heading once. We bias initial direction away from core,
    and spread builders with an ID-based tie-break when on/near center.
    """
    if state.spiral_initialized:
        return

    # Cardinal order used by the square spiral.
    # 0:EAST, 1:SOUTH, 2:WEST, 3:NORTH
    if state.core_position != Position(-1, -1):
        dx = my_pos.x - state.core_position.x
        dy = my_pos.y - state.core_position.y

        if abs(dx) > abs(dy):
            state.spiral_heading_idx = 0 if dx >= 0 else 2
        elif abs(dy) > 0:
            state.spiral_heading_idx = 1 if dy >= 0 else 3
        else:
            state.spiral_heading_idx = ct.get_id() % 4
    else:
        state.spiral_heading_idx = ct.get_id() % 4

    state.spiral_leg_length = 1
    state.spiral_steps_on_leg = 0
    state.spiral_legs_completed = 0
    state.spiral_initialized = True


def _get_spiral_direction(state: BuilderBotState) -> Direction:
    directions = [Direction.EAST, Direction.SOUTH, Direction.WEST, Direction.NORTH]
    return directions[state.spiral_heading_idx % 4]


def _rotate_spiral_heading(state: BuilderBotState) -> None:
    state.spiral_heading_idx = (state.spiral_heading_idx + 1) % 4


def _advance_spiral_after_success(state: BuilderBotState) -> None:
    """
    Advance square-spiral counters after a successful exploration move.
    Spiral leg lengths grow as 1,1,2,2,3,3,...
    """
    state.spiral_steps_on_leg += 1
    if state.spiral_steps_on_leg < state.spiral_leg_length:
        return

    state.spiral_steps_on_leg = 0
    state.spiral_heading_idx = (state.spiral_heading_idx + 1) % 4
    state.spiral_legs_completed += 1
    if state.spiral_legs_completed % 2 == 0:
        state.spiral_leg_length += 1


def _get_nearest_enemy_infrastructure(ct: Controller, my_pos: Position) -> Position | None:
    """
    Returns nearest visible enemy building position (excluding markers).
    """
    my_team = ct.get_team()
    nearest = None
    nearest_dist = float("inf")

    for building_id in ct.get_nearby_buildings():
        if ct.get_team(building_id) == my_team:
            continue
        if ct.get_entity_type(building_id) == EntityType.MARKER:
            continue

        enemy_pos = ct.get_position(building_id)
        dist = my_pos.distance_squared(enemy_pos)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = enemy_pos

    return nearest


def _get_enemy_follow_direction(ct: Controller, state: BuilderBotState, my_pos: Position, enemy_pos: Position) -> Direction | None:
    """
    Returns a direction that moves roughly tangentially along enemy infrastructure,
    instead of turning directly away.

    We try both tangential directions around the enemy vector, then fallback to
    a short local scoring pass for legal candidates.
    """
    dx = enemy_pos.x - my_pos.x
    dy = enemy_pos.y - my_pos.y

    # Tangent vectors relative to enemy vector (dx, dy): (-dy, dx) and (dy, -dx)
    tangential_dirs = _dirs_from_delta_priority(-dy, dx) + _dirs_from_delta_priority(dy, -dx)

    for direction in tangential_dirs:
        if direction == Direction.CENTRE:
            continue
        outcome = _simulate_move_legality(ct, direction)
        if outcome == "ok":
            return direction

    # Secondary option: pick a nearby direction that stays mobile and avoids immediate backtrack.
    best = None
    previous_pos = _get_previous_position(state)
    for direction in DIRECTIONS:
        outcome = _simulate_move_legality(ct, direction)
        if outcome == "blocked":
            continue

        tile = my_pos.add(direction)
        score = 0.0
        if previous_pos is not None and tile == previous_pos:
            score -= EXPLORATION_BACKTRACK_PENALTY

        # Prefer progressing outward while tracing enemy edge.
        if state.core_position != Position(-1, -1):
            score += tile.distance_squared(state.core_position)

        # Prefer staying close enough to continue edge-follow behaviour.
        score -= 0.4 * tile.distance_squared(enemy_pos)

        if best is None or score > best[0]:
            best = (score, direction)

    if best is None:
        return None
    return best[1]


def _dirs_from_delta_priority(dx: int, dy: int) -> list[Direction]:
    """
    Converts a free-form delta intent into an ordered list of candidate directions.
    """
    primary = _direction_from_sign(dx, dy)
    candidates = []
    if primary is not None:
        candidates.append(primary)

    if dx != 0 and dy != 0:
        cardinal_x = Direction.EAST if dx > 0 else Direction.WEST
        cardinal_y = Direction.SOUTH if dy > 0 else Direction.NORTH
        candidates.extend([cardinal_x, cardinal_y])
    elif dx != 0:
        candidates.append(Direction.EAST if dx > 0 else Direction.WEST)
    elif dy != 0:
        candidates.append(Direction.SOUTH if dy > 0 else Direction.NORTH)

    # De-duplicate while preserving order.
    deduped = []
    for direction in candidates:
        if direction not in deduped:
            deduped.append(direction)
    return deduped


def _direction_from_sign(dx: int, dy: int) -> Direction | None:
    sx = 0 if dx == 0 else (1 if dx > 0 else -1)
    sy = 0 if dy == 0 else (1 if dy > 0 else -1)

    mapping = {
        (1, 0): Direction.EAST,
        (-1, 0): Direction.WEST,
        (0, 1): Direction.SOUTH,
        (0, -1): Direction.NORTH,
        (1, 1): Direction.SOUTHEAST,
        (1, -1): Direction.NORTHEAST,
        (-1, 1): Direction.SOUTHWEST,
        (-1, -1): Direction.NORTHWEST,
    }
    return mapping.get((sx, sy))


def _simulate_move_legality(ct: Controller, direction: Direction) -> str:
    """
    Cheap movement viability check used by exploration steering.
    Returns "ok" or "blocked".
    """
    if ct.get_move_cooldown() > 0:
        return "blocked"

    if ct.can_move(direction):
        return "ok"

    my_pos = ct.get_position()
    next_pos = my_pos.add(direction)
    if not logic_utils.is_position_in_bounds(ct, next_pos):
        return "blocked"

    if not ct.is_in_vision(next_pos):
        return "blocked"

    if _is_diagonal_direction(direction):
        detour = _choose_diagonal_detour(ct, direction)
        if detour is not None:
            return "ok"

    occupying_builder_id = ct.get_tile_builder_bot_id(next_pos)
    if occupying_builder_id is not None and occupying_builder_id != ct.get_id():
        return "blocked"

    back_direction = next_pos.direction_to(my_pos)
    if not _is_diagonal_direction(back_direction) and ct.can_build_conveyor(next_pos, back_direction):
        return "ok"

    return "blocked"


def _is_small_loop_pattern(state: BuilderBotState) -> bool:
    """
    Detects tight exploration loops like A-B-A-B and 3-tile cycles.
    """
    if len(state.recent_positions) < 6:
        return False

    window = state.recent_positions[-6:]
    if len(set(window)) <= 3:
        return True

    # 2-cycle: p0==p2==p4 and p1==p3==p5
    if window[0] == window[2] == window[4] and window[1] == window[3] == window[5]:
        return True

    return False


def _pick_explore_escape_direction(ct: Controller, state: BuilderBotState, my_pos: Position) -> Direction | None:
    """
    Aggressive loop-break direction picker for side/corner traps.
    """
    best = None
    current_round = ct.get_current_round()
    recent_set = set(state.recent_positions[-EXPLORATION_MEMORY_WINDOW:])

    for direction in DIRECTIONS:
        outcome = _simulate_move_legality(ct, direction)
        if outcome == "blocked":
            continue

        tile = my_pos.add(direction)
        score = 0.0

        if (tile.x, tile.y) in recent_set:
            score -= 250

        # Strong outward pressure from core.
        if state.core_position != Position(-1, -1):
            score += 3.0 * tile.distance_squared(state.core_position)

        # Prefer unknown/stale tiles.
        seen = state.known_map.get((tile.x, tile.y))
        if seen is None:
            score += 150
        else:
            _, seen_round = seen
            score += min(40, current_round - seen_round)

        if best is None or score > best[0]:
            best = (score, direction)

    if best is None:
        return None
    return best[1]


def _force_spiral_jump(state: BuilderBotState, ct: Controller) -> None:
    """
    Deterministically perturbs spiral state to break side/corner dead cycles.
    """
    jump = 1 + ((ct.get_current_round() + ct.get_id()) % 3)
    state.spiral_heading_idx = (state.spiral_heading_idx + jump) % 4
    state.spiral_steps_on_leg = 0
    state.spiral_leg_length = min(state.spiral_leg_length + 1, 9)
    state.spiral_legs_completed += 1


def _a_star_path(ct: Controller, start: Position, goal: Position) -> list[Direction] | None:
    """
    Weighted A* search with a node budget cap.
    """
    if start == goal:
        return []

    open_heap = []
    heapq.heappush(open_heap, (logic_utils.chebyshev_distance(start, goal), 0, start))

    came_from: dict[Position, Position] = {}
    g_score: dict[Position, float] = {start: 0}
    already_explored: set[Position] = set()
    tie_breaker = 0
    expanded_nodes = 0

    while open_heap and expanded_nodes < PATHFIND_NODE_BUDGET:
        _, _, current = heapq.heappop(open_heap)
        if current in already_explored:
            continue

        if current == goal:
            return _reconstruct_path(start, goal, came_from)

        already_explored.add(current)
        expanded_nodes += 1

        for direction in DIRECTIONS:
            neighbor = current.add(direction)

            if not logic_utils.is_position_in_bounds(ct, neighbor):
                continue
            if not ct.is_in_vision(neighbor):
                continue
            if neighbor in already_explored:
                continue

            move_cost = _get_tile_move_cost(ct, neighbor, allow_goal=(neighbor == goal))
            if move_cost == IMPASSABLE_TILE_COST:
                continue

            tentative_g = g_score[current] + move_cost
            if tentative_g >= g_score.get(neighbor, float("inf")):
                continue

            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            tie_breaker += 1
            heuristic = logic_utils.chebyshev_distance(neighbor, goal) * PASSABLE_TILE_COST
            f_score = tentative_g + heuristic
            heapq.heappush(open_heap, (f_score, tie_breaker, neighbor))

    return None


def _reconstruct_path(start: Position, goal: Position, came_from: dict[Position, Position]) -> list[Direction] | None:
    """
    Reconstructs direction list from A* predecessor map.
    """
    if start == goal:
        return []

    if goal not in came_from:
        return None

    nodes = [goal]
    node = goal
    while node != start:
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


def _try_move_with_optional_conveyor(ct: Controller, direction: Direction) -> str:
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

    if ct.can_move(direction):
        ct.move(direction)
        return "moved"

    # If a diagonal target tile is currently unwalkable, we cannot fix it by placing
    # a diagonal conveyor. Try one-step cardinal detour and let caller replan.
    if _is_diagonal_direction(direction):
        detour = _choose_diagonal_detour(ct, direction)
        if detour is not None:
            detour_outcome = _try_move_with_optional_conveyor(ct, detour)
            if detour_outcome in ("moved", "detour_moved"):
                return "detour_moved"

    my_pos = ct.get_position()
    next_pos = my_pos.add(direction)
    if not logic_utils.is_position_in_bounds(ct, next_pos):
        return "permanent_block"

    occupying_builder_id = ct.get_tile_builder_bot_id(next_pos)
    if occupying_builder_id is not None and occupying_builder_id != ct.get_id():
        return "temporary_block"

    back_direction = next_pos.direction_to(my_pos)
    if not _is_diagonal_direction(back_direction) and ct.can_build_conveyor(next_pos, back_direction):
        ct.build_conveyor(next_pos, back_direction)
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
    state.current_path = []
    state.blocked_turns = 0


def _reset_after_harvester_build(state: BuilderBotState) -> None:
    """
    Clears mission state after successful harvester build.
    """
    state.mode = MODE_IDLE
    state.target_ore = None
    state.target_adjacent_tile = None
    state.current_path = []
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


def _choose_diagonal_detour(ct: Controller, diagonal_direction: Direction) -> Direction | None:
    """
    For a blocked diagonal attempt, choose one cardinal one-step detour.

    Preference:
    1. Immediately movable cardinal step.
    2. Cardinal step where we can place a conveyor and then move.
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

        back_direction = mid.direction_to(my_pos)
        if _is_diagonal_direction(back_direction):
            continue

        if ct.can_build_conveyor(mid, back_direction):
            return candidate

    return None


def _get_tile_move_cost(ct: Controller, pos: Position, allow_goal: bool = False) -> float:
    """
    Returns tile move cost based on navigability and passability.
    """
    if not _is_navigable_tile(ct, pos, allow_goal=allow_goal):
        return IMPASSABLE_TILE_COST

    if ct.is_tile_passable(pos):
        return PASSABLE_TILE_COST

    return EMPTY_TILE_COST


def _is_navigable_tile(ct: Controller, pos: Position, allow_goal: bool = False) -> bool:
    """
    Returns whether tile can be considered route-navigable for pathfinding.
    """
    if not logic_utils.is_position_in_bounds(ct, pos):
        return False

    if not ct.is_in_vision(pos):
        return False

    occupying_builder_id = ct.get_tile_builder_bot_id(pos)
    if occupying_builder_id is not None and occupying_builder_id != ct.get_id():
        return False

    env = ct.get_tile_env(pos)
    if env == Environment.WALL:
        return False

    building_id = ct.get_tile_building_id(pos)
    if building_id is not None:
        building_type = ct.get_entity_type(building_id)

        if building_type in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.ROAD):
            return True
        if building_type == EntityType.CORE and ct.get_team(building_id) == ct.get_team():
            return True

        return False

    return env in (Environment.EMPTY, Environment.ORE_TITANIUM, Environment.ORE_AXIONITE)


def _record_recent_position(state: BuilderBotState, pos: Position) -> None:
    """
    Tracks a short rolling history of this bot's recent positions.
    """
    xy = (pos.x, pos.y)
    state.recent_positions.append(xy)
    if len(state.recent_positions) > EXPLORATION_MEMORY_WINDOW:
        state.recent_positions.pop(0)


def _get_previous_position(state: BuilderBotState) -> Position | None:
    """
    Returns immediately previous position if available.
    """
    if len(state.recent_positions) < 2:
        return None

    x, y = state.recent_positions[-2]
    return Position(x, y)


def _encode_marker_value(kind: int, payload: int) -> int:
    payload_clamped = payload & MARKER_PAYLOAD_MASK
    return (kind << MARKER_KIND_SHIFT) | payload_clamped


def _decode_marker_value(value: int) -> tuple[int, int]:
    kind = value >> MARKER_KIND_SHIFT
    payload = value & MARKER_PAYLOAD_MASK
    return kind, payload


def _try_place_visit_marker(ct: Controller) -> None:
    """
    Places a friendly visit marker on current tile when legal.
    """
    current_pos = ct.get_position()
    if ct.can_place_marker(current_pos):
        marker_value = _encode_marker_value(MARKER_KIND_VISIT, ct.get_current_round())
        ct.place_marker(current_pos, marker_value)


def _read_visit_marker_round(ct: Controller, pos: Position) -> int | None:
    """
    Reads visit round from friendly marker at pos when available.
    """
    if not ct.is_in_vision(pos):
        return None

    building_id = ct.get_tile_building_id(pos)
    if building_id is None:
        return None

    if ct.get_entity_type(building_id) != EntityType.MARKER:
        return None

    if ct.get_team(building_id) != ct.get_team():
        return None

    marker_value = ct.get_marker_value(building_id)
    marker_kind, marker_payload = _decode_marker_value(marker_value)
    if marker_kind == MARKER_KIND_VISIT:
        return marker_payload

    if marker_kind == MARKER_KIND_CORE_SPAWN_LANE:
        return None

    return None

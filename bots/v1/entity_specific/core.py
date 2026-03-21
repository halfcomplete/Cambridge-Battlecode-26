from constants import (
    MARKER_KIND_CORE_SPAWN_LANE,
    MARKER_KIND_SHIFT,
    MARKER_PAYLOAD_MASK,
)
import logic_utils

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, EntityType, Position  # type: ignore


class CoreState:
    """
    Core state for spawn scheduling and lane diversification.

    Fields:
    - num_spawned: retained from the original behaviour.
    - spawn_rotation_index: rotating tie-break index for lane selection.
    - last_spawn_pos: used to avoid repeating the same spawn tile when alternatives exist.
    """

    def __init__(self):
        self.num_spawned = 0
        self.spawn_rotation_index = 0
        self.last_spawn_pos: Position | None = None


def execute_behaviour(ct: Controller, state: CoreState) -> None:
    """
    Main core behaviour.

    We keep the original spawn cap behaviour, but replace random spawn selection
    with a marker-informed lane scheduler that reduces congo-line spawning.
    """
    if state.num_spawned >= 3:
        return

    center = ct.get_position()
    spawn_tiles = _get_core_spawn_tiles(center)

    candidates = []
    for index, tile in enumerate(spawn_tiles):
        if not ct.can_spawn(tile):
            continue

        lane_anchor = _lane_anchor_for_spawn(center, tile, state.spawn_rotation_index)
        lane_round = _read_lane_marker_round(ct, lane_anchor)

        repeated_tile_penalty = 1 if (state.last_spawn_pos is not None and tile == state.last_spawn_pos) else 0
        lane_age_key = lane_round if lane_round is not None else -1
        rotation_key = (index - state.spawn_rotation_index) % len(spawn_tiles)

        candidates.append((repeated_tile_penalty, lane_age_key, rotation_key, tile, lane_anchor, index))

    if not candidates:
        return

    # Lower key is better:
    # 1) avoid repeating same spawn tile when alternatives exist,
    # 2) prefer least-recently-used lane marker,
    # 3) use rotation as deterministic tie-break.
    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    _, _, _, chosen_spawn, lane_anchor, chosen_index = candidates[0]

    ct.spawn_builder(chosen_spawn)
    state.num_spawned += 1
    state.last_spawn_pos = chosen_spawn
    state.spawn_rotation_index = (chosen_index + 1) % len(spawn_tiles)

    _try_place_lane_marker(ct, lane_anchor)


def _get_core_spawn_tiles(center: Position) -> list[Position]:
    """
    Returns all 9 core tiles (3x3 around the core center), deterministic order.
    """
    tiles = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            tiles.append(Position(center.x + dx, center.y + dy))
    return tiles


def _lane_anchor_for_spawn(center: Position, spawn_tile: Position, rotation_index: int) -> Position:
    """
    Maps a spawn tile to a nearby perimeter tile used as a spawn-lane marker.

    The marker must be buildable/markable and is within core action radius on
    standard maps. For center spawn, we rotate among four cardinal anchors.
    """
    dx = spawn_tile.x - center.x
    dy = spawn_tile.y - center.y

    if dx == 0 and dy == 0:
        cardinal = [
            Position(center.x, center.y - 2),
            Position(center.x + 2, center.y),
            Position(center.x, center.y + 2),
            Position(center.x - 2, center.y),
        ]
        return cardinal[rotation_index % len(cardinal)]

    return Position(center.x + (2 * dx), center.y + (2 * dy))


def _encode_marker_value(kind: int, payload: int) -> int:
    payload_clamped = payload & MARKER_PAYLOAD_MASK
    return (kind << MARKER_KIND_SHIFT) | payload_clamped


def _decode_marker_value(value: int) -> tuple[int, int]:
    kind = value >> MARKER_KIND_SHIFT
    payload = value & MARKER_PAYLOAD_MASK
    return kind, payload


def _try_place_lane_marker(ct: Controller, lane_anchor: Position) -> None:
    """
    Writes a lane marker with current round at the selected spawn-lane anchor.
    """
    if not logic_utils.is_position_in_bounds(ct, lane_anchor):
        return

    if ct.can_place_marker(lane_anchor):
        marker_value = _encode_marker_value(MARKER_KIND_CORE_SPAWN_LANE, ct.get_current_round())
        ct.place_marker(lane_anchor, marker_value)


def _read_lane_marker_round(ct: Controller, lane_anchor: Position) -> int | None:
    """
    Reads friendly spawn-lane marker round at a lane anchor, if available.
    """
    if not logic_utils.is_position_in_bounds(ct, lane_anchor):
        return None

    if not ct.is_in_vision(lane_anchor):
        return None

    building_id = ct.get_tile_building_id(lane_anchor)
    if building_id is None:
        return None

    if ct.get_entity_type(building_id) != EntityType.MARKER:
        return None

    if ct.get_team(building_id) != ct.get_team():
        return None

    marker_value = ct.get_marker_value(building_id)
    marker_kind, marker_payload = _decode_marker_value(marker_value)
    if marker_kind != MARKER_KIND_CORE_SPAWN_LANE:
        return None

    return marker_payload

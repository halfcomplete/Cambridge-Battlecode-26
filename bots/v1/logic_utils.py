import math

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

def get_all_deltas_in_range(r: float) -> list:
    """
    Get all deltas of the format (x, y) such that x^2 + y^2 <= range.
    Note:
        This returns a list of tile position DELTAS within the range, NOT absolute tile positions.
        If you want a list of absolute tile positions within a range, centred around a given position,
        use `get_all_tile_positions_in_range(r, p)`.
    """
    pairs = []
    limit = int(math.sqrt(r))

    for x in range(-limit, limit + 1):
        for y in range(-limit, limit + 1):
            if x * x + y * y <= r:
                pairs.append((x, y))

    return [(x, y) for x, y in pairs]

def get_all_tile_positions_in_range(r: float, p: Position) -> list:
    """
    Get all tile positions within a given range of a given position.
    Note:
        This returns a list of absolute tile positions within the range, centred around a given position.
        If you want a list of tile position DELTAS within the range, use `get_all_deltas_in_range(r)`.
    """
    deltas = get_all_deltas_in_range(r)
    return [Position(p.x + dx, p.y + dy) for dx, dy in deltas]


def is_position_in_bounds(ct: Controller, pos: Position) -> bool:
    """
    Returns whether the given position is within the bounds of the map.
    """
    return 0 <= pos.x < ct.get_map_width() and 0 <= pos.y < ct.get_map_height()

def chebyshev_distance(a: Position, b: Position) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))

import math

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

def get_all_tiles_in_range(r) -> list[Position]:
    """
    Get all possible deltas (x, y) such that x^2 + y^2 <= range.
    """
    pairs = []
    limit = int(math.sqrt(r))

    for x in range(-limit, limit + 1):
        for y in range(-limit, limit + 1):
            if x * x + y * y <= r:
                pairs.append((x, y))

    return [Position(x, y) for x, y in pairs]
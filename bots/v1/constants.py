# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

# Non-centre directions
DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]

# Costs for different tile types, used in pathfinding logic (A*)
PASSABLE_TILE_COST = 1
EMPTY_TILE_COST = 2
IMPASSABLE_TILE_COST = float('inf')
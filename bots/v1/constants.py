# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

# Non-centre directions
DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
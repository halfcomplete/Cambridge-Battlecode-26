# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

# Non-centre directions
DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]

# Costs for different tile types, used in pathfinding logic (A*)
PASSABLE_TILE_COST = 1
EMPTY_TILE_COST = 2
IMPASSABLE_TILE_COST = float('inf')

# Builder-bot mode names
MODE_IDLE = "IDLE"
MODE_EXPLORING = "EXPLORING"
MODE_MOVING_TO_ORE = "MOVING_TO_ORE"

# Pathfinding tuning
PATHFIND_NODE_BUDGET = 220
MAX_TEMP_BLOCKED_TURNS = 3

# Exploration anti-loop tuning
EXPLORATION_MEMORY_WINDOW = 8
EXPLORATION_BACKTRACK_PENALTY = 180
EXPLORATION_RECENT_TILE_PENALTY = 90
VISIT_MARKER_FRESH_ROUNDS = 16
VISIT_MARKER_MAX_PENALTY = 120

# Marker encoding (u32)
MARKER_KIND_SHIFT = 28
MARKER_PAYLOAD_MASK = (1 << MARKER_KIND_SHIFT) - 1
MARKER_KIND_VISIT = 1
MARKER_KIND_CORE_SPAWN_LANE = 2
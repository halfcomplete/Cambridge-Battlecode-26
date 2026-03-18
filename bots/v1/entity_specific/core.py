import math
import random
from constants import DIRECTIONS

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

# Number of builder bots spawned so far
num_spawned = 0

def execute_behaviour(ct: Controller) -> None:
    """
    This function is the main entry point for main.py to run the core's behaviour logic.
    """
    
    if num_spawned < 3:
        # If we haven't spawned 3 builder bots yet, try to spawn one on a random tile
        spawn_pos = ct.get_position().add(random.choice(DIRECTIONS))
        if ct.can_spawn(spawn_pos):
            ct.spawn_builder(spawn_pos)
            num_spawned += 1
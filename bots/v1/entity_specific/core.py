import math
import random
from constants import DIRECTIONS

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

class CoreState:
    """
    Class to represent the state of a core entity, which can be used to make decisions in its behaviour logic.
    """
    def __init__(self):
        self.num_spawned = 0

def execute_behaviour(ct: Controller, state: CoreState) -> None:
    """
    This function is the main entry point for main.py to run the core's behaviour logic.
    """

    if state.num_spawned < 3:
        # If we haven't spawned 3 builder bots yet, try to spawn one on a random tile
        spawn_pos = ct.get_position().add(random.choice(DIRECTIONS))
        if ct.can_spawn(spawn_pos):
            ct.spawn_builder(spawn_pos)
            state.num_spawned += 1
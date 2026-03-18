import random, math
from constants import DIRECTIONS

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

def execute_behaviour(ct: Controller) -> None:
    """
    This function is the main entry point for main.py to run the builder bot's behaviour logic.
    """
    # If we are adjacent to an ore tile, build a harvester on it
    for d in Direction:
        check_pos = ct.get_position().add(d)
        if ct.can_build_harvester(check_pos):
            ct.build_harvester(check_pos)
            break
    
    # Move in a random direction
    move_dir = random.choice(DIRECTIONS)
    move_pos = ct.get_position().add(move_dir)
    # We need to place a conveyor or road to stand on, before we can move onto a tile
    if ct.can_build_road(move_pos):
        ct.build_road(move_pos)
    if ct.can_move(move_dir):
        ct.move(move_dir)

    # Place a marker on an adjacent tile with the current round number
    marker_pos = ct.get_position().add(random.choice(DIRECTIONS))
    if ct.can_place_marker(marker_pos):
        ct.place_marker(marker_pos, ct.get_current_round())

def determine_tile_to_move_to() -> Position:
    ...
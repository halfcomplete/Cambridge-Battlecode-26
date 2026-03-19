"""Our version 1 bot.

Each unit gets its own Player instance; the engine calls run() once per round.
Use Controller.get_entity_type() to branch on what kind of unit you are.
Five types of units: Core, Builder bot, Gunner, Sentinel, Breach, Launcher

This bot:
  - Core: spawns up to 3 builder bots on random adjacent tiles
  - Builder bot: builds a harvester on any adjacent ore tile, then moves in a
    random direction (laying a road first so the tile is passable), and places
    a marker recording the current round number
"""

import random
import math

from cambc import Controller, Direction, EntityType, Environment, Position

# non-centre directions
DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]

class Player:
    def __init__(self) -> None:
        self.num_spawned = 0 # number of builder bots spawned so far (core)

    def run(self, ct: Controller) -> None:
        self.delegate_behaviour(ct)
            
    
    def delegate_behaviour(self, ct: Controller) -> None:
        etype = ct.get_entity_type()
        if etype == EntityType.CORE:
            self.execute_core_behaviour(ct)
        elif etype == EntityType.BUILDER_BOT:
            self.execute_builder_bot_behaviour(ct)
        elif etype == EntityType.GUNNER:
            self.execute_gunner_behaviour(ct)
        elif etype == EntityType.SENTINEL:
            self.execute_sentinel_behaviour(ct)
        elif etype == EntityType.BREACH:
            self.execute_breach_behaviour(ct)
        elif etype == EntityType.LAUNCHER:
            self.execute_launcher_behaviour(ct)
        else:
            print(f"Unknown entity type: {etype}")
            pass

    def execute_core_behaviour(self, ct: Controller) -> None:
        if self.num_spawned < 3:
            # if we haven't spawned 3 builder bots yet, try to spawn one on a random tile
            spawn_pos = ct.get_position().add(random.choice(DIRECTIONS))
            if ct.can_spawn(spawn_pos):
                ct.spawn_builder(spawn_pos)
                self.num_spawned += 1
    
    def execute_builder_bot_behaviour(self, ct: Controller) -> None:
        # if we are adjacent to an ore tile, build a harvester on it
        for d in Direction:
            check_pos = ct.get_position().add(d)
            if ct.can_build_harvester(check_pos):
                ct.build_harvester(check_pos)
                break
        
        # move in a random direction
        move_dir = random.choice(DIRECTIONS)
        move_pos = ct.get_position().add(move_dir)
        # we need to place a conveyor or road to stand on, before we can move onto a tile
        if ct.can_build_road(move_pos):
            ct.build_conveyor(move_pos)
            
        if ct.can_move(move_dir):
            ct.move(move_dir)

        # place a marker on an adjacent tile with the current round number
        marker_pos = ct.get_position().add(random.choice(DIRECTIONS))
        if ct.can_place_marker(marker_pos):
            ct.place_marker(marker_pos, ct.get_current_round())

        
    def determine_tile_to_move_to() -> Position:
        ...

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
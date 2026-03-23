"""Ultra-fast Battlecode bot (NO BFS, pure greedy exploration)"""

import random

from cambc import Controller, Direction, EntityType, Position, Environment

DIRECTIONS = [
    Direction.NORTH,
    Direction.SOUTH,
    Direction.EAST,
    Direction.WEST,
]


class Player:
    def __init__(self) -> None:
        self.num_spawned = 0
        self.core_pos = None
        self.last_harvested = None

    def run(self, ct: Controller) -> None:
        if ct.get_entity_type() == EntityType.CORE:
            self.core_behaviour(ct)
        else:
            self.builder_behaviour(ct)

    # ================= CORE =================
    def core_behaviour(self, ct: Controller) -> None:
        self.core_pos = ct.get_position()

        if self.num_spawned < 7:
            pos = self.core_pos
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    target = Position(pos.x + dx, pos.y + dy)
                    if ct.can_spawn(target):
                        ct.spawn_builder(target)
                        self.num_spawned += 1
                        return

    # ================= BUILDER =================
    def builder_behaviour(self, ct: Controller) -> None:
        my_pos = ct.get_position()

        # ===== BUILD HARVESTER IF NEXT TO ORE =====
        for d in DIRECTIONS:
            adj = my_pos.add(d)
            if ct.can_build_harvester(adj):
                ct.build_harvester(adj)
                self.last_harvested = adj  # remember it

                # immediately try to move away
                away_dir = d.opposite()
                if ct.get_move_cooldown() == 0 and ct.can_move(away_dir):
                    ct.move(away_dir)

                return
        # ===== LOOK FOR ORE IN VISION =====
        target_ore = None
        min_dist = 999999

        for tile in ct.get_nearby_tiles():
            env = ct.get_tile_env(tile)
            if env in (Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
                if tile == self.last_harvested:
                    continue
                dist = my_pos.distance_squared(tile)
                if dist < min_dist:
                    min_dist = dist
                    target_ore = tile

        # ===== MOVE TOWARD ORE =====
        if target_ore:
            move_dir = my_pos.direction_to(target_ore)
        else:
            # ===== EXPLORE AWAY FROM CORE =====
            if self.core_pos:
                move_dir = self.core_pos.direction_to(my_pos)
            else:
                move_dir = random.choice(DIRECTIONS)

            # add randomness so bots spread
            if random.random() < 0.3:
                move_dir = random.choice(DIRECTIONS)

        # ===== MOVEMENT + CONVEYOR BUILD =====
        next_pos = my_pos.add(move_dir)
        back_dir = move_dir.opposite()

        # build conveyor if needed
        if not ct.is_tile_passable(next_pos):
            if ct.can_build_conveyor(next_pos, back_dir):
                ct.build_conveyor(next_pos, back_dir)
                return

        # move
        if ct.get_move_cooldown() == 0 and ct.can_move(move_dir):
            ct.move(move_dir)
        else:
            # fallback: try any direction
            for d in DIRECTIONS:
                if ct.can_move(d):
                    ct.move(d)
                    break
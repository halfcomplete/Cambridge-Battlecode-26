from cambc import Controller, Direction, Position, Environment, EntityType

DIRECTIONS = [
    Direction.NORTH,
    Direction.NORTHEAST,
    Direction.EAST,
    Direction.SOUTHEAST,
    Direction.SOUTH,
    Direction.SOUTHWEST,
    Direction.WEST,
    Direction.NORTHWEST,
]

class Player:
    def __init__(self) -> None:
        self.num_spawned = 0
        self.core_pos = None

        # path system
        self.current_path = []
        self.path_index = 0
        self.returning = False

        # per-bot memory
        self.last_pos = None

    def run(self, ct: Controller) -> None:
        self.delegate_behaviour(ct)

    def delegate_behaviour(self, ct: Controller) -> None:
        etype = ct.get_entity_type()

        if etype == EntityType.CORE:
            self.execute_core_behaviour(ct)
        elif etype == EntityType.BUILDER_BOT:
            self.execute_builder_bot_behaviour(ct)

    # ================= CORE =================
    def execute_core_behaviour(self, ct: Controller) -> None:
        self.core_pos = ct.get_position()

        if self.num_spawned < 3:
            pos = ct.get_position()

            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    target = Position(pos.x + dx, pos.y + dy)
                    if ct.can_spawn(target):
                        ct.spawn_builder(target)
                        self.num_spawned += 1
                        return

    # ================= BUILDER BOT =================
    def execute_builder_bot_behaviour(self, ct: Controller) -> None:
        self.ctrl = ct
        moved = False
        while moved == False:
            current_position = ct.get_position()
            current_direction = ct.get_direction()
            current_move = current_position+current_direction


    # ================= UTILITIES =================
    def find_nearest_ore(self, pos: Position) -> Position | None:
        """Return nearest ore tile within vision radius."""
        radius_sq = self.ctrl.get_vision_radius_sq()
        tiles = self.ctrl.get_nearby_tiles(radius_sq)
        closest = None
        min_dist = float('inf')
        for t in tiles:
            env = self.ctrl.get_tile_env(t)
            if env in [Environment.ORE_TITANIUM, Environment.ORE_AXIONITE]:
                dist = pos.distance_squared(t)
                if dist < min_dist:
                    min_dist = dist
                    closest = t
        return closest

import random

from cambc import Controller, Direction, EntityType, Environment, Position

# non-centre directions
SPAWN_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
# Job types:
PAVER = 0
BUILDER = 1
EXPLORER = 2

DIRECTIONS4 = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
#this code is roughly equivelent to a while loop
#with __init__ being run outside the loop, and run() being run once per iteration
class Player:
  def __init__(self):
    #variables created here will be remembered across rounds, and can be used in run()
    #but not remembered across different bots
    self.num_spawned = 0 # number of builder bots spawned so far (core)
    # direction to move in (builder bot) - conveyors (and the opposite-direction logic below) assume cardinal moves
    self.move_dir = random.choice(DIRECTIONS4)
    self.rev_dir = Direction.opposite(self.move_dir) # direction opposite to move_dir, used for building conveyors
    self.stuck = 0 # counter for calculating how long a bot has been on friendly territory in effort to get him to not stay on paths he has already made

  def run(self, ct: Controller) -> None:
    #ct is the thing we are controlling
    #self is a python thing, lets us refer to stuff set in __init__ (and elsewhere when we get there)
    entityType = ct.get_entity_type()
    if entityType == EntityType.CORE:
      #controlling the core
      if self.num_spawned >= 3:
        return
      # if we haven't spawned 3 builder bots yet, try to spawn one on a random tile
      spawn_pos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS))
      if not ct.can_spawn(spawn_pos):
        return
      ct.spawn_builder(spawn_pos)
      self.num_spawned += 1

    elif entityType == EntityType.BUILDER_BOT:
      if (self.num_spawned % 3) == PAVER:
        # controlling a paver bot
        # if we are adjacent to an ore tile, build a harvester on it
        for d in Direction:
          check_pos = ct.get_position().add(d)
          if ct.can_build_harvester(check_pos):
            ct.build_harvester(check_pos)
            #because we build a harvester, we can't build a conveyor this round.
            #because we can't build a conveyor, we might not be able to move.
            #because we might not be able to move, we might think we're stuck on a wall
            #to avoid that, just stop the turn here.
            return

        # move in set direction
        move_pos = ct.get_position().add(self.move_dir)

        # If we would move into an enemy entity, pick a new direction instead.
        if self._is_enemy_entity_at(ct, move_pos):
          self.changeMoveDir()
        else:
          # we need to place a conveyor or road to stand on, before we can move onto a tile
          if ct.can_build_conveyor(move_pos, self.rev_dir):
            ct.build_conveyor(move_pos, self.rev_dir)
          #this extra can_move check is because we might have built a harvester, and so couldn't build a road
          if ct.can_move(self.move_dir):
            ct.move(self.move_dir)
          else:
            self.changeMoveDir()

        # place a marker on an adjacent tile with the current round number
        marker_pos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS))
        if ct.can_place_marker(marker_pos):
          ct.place_marker(marker_pos, ct.get_current_round())

  def _is_enemy_entity_at(self, ct: Controller, pos: Position) -> bool:
    # Avoid calling tile queries out-of-bounds.
    if pos.x < 0 or pos.y < 0 or pos.x >= ct.get_map_width() or pos.y >= ct.get_map_height():
      return False

    # Enemy builder bot?
    builder_id = ct.get_tile_builder_bot_id(pos)
    if builder_id is not None and ct.get_team(builder_id) != ct.get_team():
      return True

    # Enemy building?
    building_id = ct.get_tile_building_id(pos)
    if building_id is not None and ct.get_team(building_id) != ct.get_team():
      return True

    return False

  def changeMoveDir(self):
    #exclude the current direction and turning back.
    possibleDirections = [d for d in DIRECTIONS4 if d != self.move_dir and d != self.rev_dir]
    self.move_dir = random.choice(possibleDirections)
    self.rev_dir = Direction.opposite(self.move_dir)
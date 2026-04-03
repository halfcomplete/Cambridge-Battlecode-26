# Main code for Cambridge Battlecode 2026
# Team Mind of Metal and Wheels
# Author: Multiple, March 2026. Α⳩ω

import random
import pathfinding
import sys

from cambc import Controller, Direction, EntityType, Environment, Position

# non-centre directions
SPAWN_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
# Job types:
PAVER = 0
BUILDER = 1
EXPLORER = 2

DIRECTIONS4 = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
class Player:
  def __init__(self):
    self.numSpawned = 0 # number of builder bots spawned so far (core)
    # direction to move in (builder bot) - conveyors (and the opposite-direction logic below) assume cardinal moves
    self.moveDir = random.choice(DIRECTIONS4)
    self.revDir = Direction.opposite(self.moveDir) # direction opposite to move_dir, used for building conveyors
    self.doublePlaced = 0

  def run(self, ct: Controller) -> None:
    entityType = ct.get_entity_type()

    # ----------------------------------------------
    # Core logic
    # ----------------------------------------------
    if entityType == EntityType.CORE:
      if self.numSpawned >= 3:
        return
      spawn_pos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS))
      if not ct.can_spawn(spawn_pos):
        return
      ct.spawn_builder(spawn_pos)

      # Increment numSpawned by 1
      self.numSpawned += 1

      # place a marker on an adjacent tile with the job number of the bot
      markerPos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS)).add(random.choice(SPAWN_DIRECTIONS))
      if ct.can_place_marker(markerPos):
        ct.place_marker(markerPos, self.numSpawned % 3)

    # ----------------------------------------------
    # Builder bot logic
    # ----------------------------------------------
    elif entityType == EntityType.BUILDER_BOT:
      #make sure we can afford a harvester, and not just wander around spamming conveyors
      #random is to make sure bots run later during the turn don't get entirely excluded by earlier bots using up the Titanium
      if(ct.get_global_resources()[0] < ct.get_harvester_cost()[0] * (1+random.random()/4)):
        return
      
      # move logic
      while True:
        builtForward = False
        movePos = ct.get_position().add(self.moveDir)

        for d in DIRECTIONS4:
          checkPos = ct.get_position().add(d)
          if ct.can_build_harvester(checkPos):
            ct.build_harvester(checkPos)
            #just made a harvester, can't make a conveyor to move onto
            return

        # Move away from enemy territory
        if self.isEnemyAt(ct, movePos):
          self.changeMoveDir()
          continue
        if ct.can_build_conveyor(movePos, self.revDir):
          ct.build_conveyor(movePos, self.revDir)

          sideDir = self.moveDir.rotate_right().rotate_right()
          sidePos = movePos.add(sideDir)

          if ct.can_build_conveyor(sidePos, self.revDir) and self.doublePlaced < 8:
            ct.build_conveyor(sidePos, self.revDir)
            self.doublePlaced += 1
            builtForward = True
        elif ct.can_move(self.moveDir):
          #THIS IS BROKEN AND NEEDS MORE TESTING
          #can't build but can move means we are conveyor following
          leftPos = ct.get_position().add(self.moveDir.rotate_left().rotate_left())
          rightPos = ct.get_position().add(self.moveDir.rotate_right().rotate_right())
          leftCheck = self.posIsInbounds(ct, leftPos) and ct.is_tile_empty(leftPos) and not ct.is_tile_passable(leftPos)
          rightCheck = self.posIsInbounds(ct, rightPos) and ct.is_tile_empty(rightPos) and not ct.is_tile_passable(rightPos)
          if((leftCheck or rightCheck) and random.random()<0.9):
            #this can get caught in an infinite loop and I'm not sure why.
            #so I threw a random chance on this to break out.
            self.changeMoveDir()
            continue
          if(random.random()<0.1):
            self.changeMoveDir()
            continue

        if ct.can_move(self.moveDir):
          ct.move(self.moveDir)
          if builtForward and self.doublePlaced < 8:
            self.placeSideNext = True
          break
        self.changeMoveDir()

      # place a marker on an adjacent tile with the current round number
      # holdover from starter bot
      # markerPos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS))
      # if ct.can_place_marker(markerPos):
      #   ct.place_marker(markerPos, ct.get_current_round())

    # ----------------------------------------------
    # Gunner turret logic
    # ----------------------------------------------
    elif entityType == EntityType.GUNNER:
      # if a target is in range, shoot it
      target = ct.get_gunner_target()
      if target != None:
        ct.fire(target);

  def posIsInbounds(self, ct: Controller, pos: Position) -> bool:
    if pos.x < 0 or pos.y < 0 or pos.x >= ct.get_map_width() or pos.y >= ct.get_map_height():
      return False
    return True

  def isEnemyAt(self, ct: Controller, pos: Position) -> bool:
    # Avoid calling tile queries out-of-bounds.
    inBounds = self.posIsInbounds(ct, pos)
    if not inBounds: 
      print("oob")
      return False
    # Enemy builder bot?
    #TODO consider removing, may not ever be relevant.
    botId = ct.get_tile_builder_bot_id(pos)
    if botId is not None and ct.get_team(botId) != ct.get_team():
      return True

    # Enemy building?
    buildingId = ct.get_tile_building_id(pos)
    if buildingId is not None and ct.get_team(buildingId) != ct.get_team() and ct.get_entity_type(buildingId) != EntityType.MARKER:
      return True

    return False

  def changeMoveDir(self):
    #exclude the current direction and turning back.
    possibleDirections = [d for d in DIRECTIONS4 if d != self.moveDir and d != self.revDir]
    self.moveDir = random.choice(possibleDirections)
    self.revDir = Direction.opposite(self.moveDir)
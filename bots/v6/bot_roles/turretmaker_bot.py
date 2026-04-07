

import random

from cambc import  Controller, Direction, EntityType, Environment, Position, GameError
import pathfinding as pfind
from bot_roles.builder_base import BuilderBase

class TurretmakerBot(BuilderBase):
  def __init__(self):
    super().__init__()
    self.possibleEnemyCorePositions = []
  
  
  
  def run(self, ct: Controller) -> None:
    # # make sure we can afford a harvester, and not just wander around spamming conveyors
    # # random is to make sure bots run later during the turn don't get entirely excluded by earlier bots using up the Titanium
    # if ct.get_global_resources()[0] < ct.get_harvester_cost()[0] * (1 + random.random() / 4):
    #   return


    #find enemy core
    nearby_tiles = ct.get_nearby_tiles()
    for potentialPos in self.possibleEnemyCorePositions:
      if potentialPos not in nearby_tiles:
        continue
      building = ct.get_tile_building_id(potentialPos)
      if(building != EntityType.CORE or ct.get_team()==ct.get_team(building)):
        self.possibleEnemyCorePositions.remove(potentialPos)
        break
      if( ct.get_entity_type(building)==EntityType.CORE and ct.get_team()!=ct.get_team(building)):
        self.possibleEnemyCorePositions = [potentialPos]

      
    if self.tryBuildGunner(ct):
      return

    
    
    i = 0
    while True:
      builtForward = False
      movePos = ct.get_position().add(self.moveDir)

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
      elif self.posIsInbounds(ct, movePos) and ct.get_entity_type(ct.get_tile_building_id(movePos)) == EntityType.ROAD and ct.get_team(ct.get_tile_building_id(movePos)) == ct.get_team():
        ct.destroy(movePos)
        try: 
          ct.build_conveyor(movePos, self.revDir)
        except GameError:
          print("Failed to build conveyor after destroying road, skipping turn")
      elif ct.can_move(self.moveDir):
        # THIS IS BROKEN AND NEEDS MORE TESTING
        # can't build but can move means we are conveyor following
        leftPos = ct.get_position().add(self.moveDir.rotate_left().rotate_left())
        rightPos = ct.get_position().add(self.moveDir.rotate_right().rotate_right())
        leftCheck = self.posIsInbounds(ct, leftPos) and ct.is_tile_empty(leftPos) and not ct.is_tile_passable(leftPos)
        rightCheck = self.posIsInbounds(ct, rightPos) and ct.is_tile_empty(rightPos) and not ct.is_tile_passable(rightPos)
        if (leftCheck or rightCheck) and random.random() < 0.9:
          # this can get caught in an infinite loop and I'm not sure why.
          # so I threw a random chance on this to break out.
          self.changeMoveDir()
          continue
        if random.random() < 0.1:
          self.changeMoveDir()
          continue

      if ct.can_move(self.moveDir):
        ct.move(self.moveDir)
        if builtForward and self.doublePlaced < 8:
          self.placeSideNext = True
        break
      self.changeMoveDir()
      if i > 5:
        return
      i += 1



  def tryBuildGunner(self, ct: Controller):
    i = 0
    xAve = 0
    yAve = 0
    for potPos in self.possibleEnemyCorePositions:
      xAve += potPos.x
      yAve += potPos.y
      i+=1
    if len(self.possibleEnemyCorePositions) == 0:
      return False
    xAve /= i
    yAve /= i
    aimingPos = Position(xAve,yAve)
    print(self.possibleEnemyCorePositions)
    print(aimingPos)

    #is the core nearby
    nearbyBuildingIds = ct.get_nearby_buildings()
    core = None
    for buildingId in nearbyBuildingIds:
      if ct.get_entity_type(buildingId) == EntityType.CORE:
        core = buildingId
    if not core:
      return False
    
    #get all possible places we can build right now
    myPos = ct.get_position()
    buildablePositions = []
    for dir in pfind.OCT_DIRECTIONS:
      testPos = myPos.add(dir)
      if not self.posIsInbounds(ct, testPos):
        continue
      if ct.get_tile_env(testPos) != Environment.EMPTY or ct.get_tile_env(testPos) != Environment.CONVEYOR or not ct.can_build_gunner(testPos, testPos.direction_to(aimingPos)):
        continue
      buildablePositions.append(testPos)

    if len(buildablePositions) == 0:
      return False
    print("hey3")

    corePos = ct.get_position(core)
    for dir in pfind.QUAD_DIRECTIONS:
      testPos = corePos.add(dir).add(dir)
      if testPos in buildablePositions:
        if ct.get_tile_env(testPos) == Environment.CONVEYOR:
          ct.destroy(testPos)
        print("hey67", testPos)
        ct.build_gunner(testPos, testPos.direction_to(aimingPos))
        return True
      testPos = corePos.add(dir).add(dir).add(dir)
      if testPos in buildablePositions:
        if ct.get_tile_env(testPos) == Environment.CONVEYOR:
          ct.destroy(testPos)
        print("hey67", testPos)
        ct.build_gunner(testPos, testPos.direction_to(aimingPos))
        return True

#cambc run --watch v6 dummy Gunnertest2




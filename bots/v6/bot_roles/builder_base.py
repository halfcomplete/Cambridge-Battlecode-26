
import random

from cambc import Controller, Direction, EntityType, Position
import pathfinding as pfind

DIRECTIONS4 = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]

class BuilderBase:
  def __init__(self):
    # direction to move in - conveyors (and the opposite-direction logic below) assume cardinal moves
    self.moveDir = random.choice(DIRECTIONS4)
    self.revDir = Direction.opposite(self.moveDir) # direction opposite to moveDir, used for building conveyors
    self.doublePlaced = 0
    self.roleColor = [255,255,255]

  def startup(self, ct):
    #nothin
    return

  def posIsInbounds(self, ct: Controller, pos: Position) -> bool:
    if pos.x < 0 or pos.y < 0 or pos.x >= ct.get_map_width() or pos.y >= ct.get_map_height():
      return False
    return True

  def isEnemyAt(self, ct: Controller, pos: Position) -> bool:
    # Avoid calling tile queries out-of-bounds.
    inBounds = self.posIsInbounds(ct, pos)
    if not inBounds:
      return False

    # Enemy builder bot?
    botId = ct.get_tile_builder_bot_id(pos)
    if botId is not None and ct.get_team(botId) != ct.get_team():
      return True

    # Enemy building?
    buildingId = ct.get_tile_building_id(pos)
    if buildingId is not None and ct.get_team(buildingId) != ct.get_team() and ct.get_entity_type(buildingId) != EntityType.MARKER:
      return True

    return False

  def changeMoveDir(self):
    # exclude the current direction and turning back.
    possibleDirections = [d for d in DIRECTIONS4 if d != self.moveDir and d != self.revDir]
    self.moveDir = random.choice(possibleDirections)
    self.revDir = Direction.opposite(self.moveDir)

  def tryBuildAdjacentHarvester(self, ct: Controller) -> bool:
    for d in DIRECTIONS4:
      checkPos = ct.get_position().add(d)
      if ct.can_build_harvester(checkPos):
        ct.build_harvester(checkPos)
        return True
    return False


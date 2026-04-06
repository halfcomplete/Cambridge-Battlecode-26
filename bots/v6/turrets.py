

from cambc import Controller, Direction, EntityType, Environment, Position
import random, sys

class Turret():
  def __new__(cls, eType: EntityType):
    match eType:
      case EntityType.GUNNER:
        return Gunner()
      case EntityType.SENTINEL:
        return Sentinel()
    print("can't find turret type error!", eType, file=sys.stderr)

class Gunner():
  def __init__(self):
    pass

  def startup(self, ct):
    #nothin
    return

  def run(self, ct: Controller):
    nearbyBuildings = ct.get_nearby_buildings()
    random.shuffle(nearbyBuildings)
    for building in nearbyBuildings:
      if ct.get_team() == ct.get_team(building):
        continue
      if ct.get_entity_type(building) == EntityType.HARVESTER:
        continue
      buildingPos = ct.get_position(building)
      if not ct.can_fire(buildingPos):
        continue
      entityType = ct.get_entity_type(building)
      if entityType == EntityType.CORE:
        ct.fire(buildingPos)
        break
      continue
    return
    
class Sentinel():
  def startup(self, ct):
    #nothin
    return
  def run(self, ct: Controller):
    nearbyBuildings = ct.get_nearby_buildings()
    random.shuffle(nearbyBuildings)
    for building in nearbyBuildings:
      if ct.get_team() == ct.get_team(building):
        continue
      if ct.get_entity_type(building) == EntityType.HARVESTER:
        continue
      buildingPos = ct.get_position(building)
      if not ct.can_fire(buildingPos):
        continue
      ct.fire(buildingPos)
      break
    return


import random

from cambc import  Controller, Direction, EntityType, Environment, Position

from bot_roles.builder_base import BuilderBase

class TurretmakerBot(BuilderBase):
  def run(self, ct: Controller) -> None:
    # # make sure we can afford a harvester, and not just wander around spamming conveyors
    # # random is to make sure bots run later during the turn don't get entirely excluded by earlier bots using up the Titanium
    # if ct.get_global_resources()[0] < ct.get_harvester_cost()[0] * (1 + random.random() / 4):
    #   return

    # move logic
    i = 0
    while True:
      pos = ct.get_position()
      builtForward = False
      movePos = pos.add(self.moveDir)

      # Get all entities and target enemy cores
      entList = ct.get_nearby_entities()
      print(entList)
      for entity in entList:
        entityType = ct.get_entity_type(entity)
        if entityType == EntityType.CORE:
          turretLoc = ct.get_position(entity)
          if ct.can_build_gunner(pos, pos.direction_to(turretLoc)):
            ct.build_gunner(pos, pos.direction_to(turretLoc))

      # # Move away from enemy territory
      # if self.isEnemyAt(ct, movePos):
      #   self.changeMoveDir()
      #   continue

      if ct.can_build_road(movePos):
        ct.build_road(movePos)

        sideDir = self.moveDir.rotate_right().rotate_right()
        sidePos = movePos.add(sideDir)

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
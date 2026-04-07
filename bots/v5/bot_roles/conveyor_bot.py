

import random

from cambc import Controller, EntityType

from bot_roles.builder_base import BuilderBase
import pathfinding as pfind
from bot_roles.suicide_bot import SuicideBot

SUICIDE_BOT_CHANCE = 0.01

class ConveyorBot(BuilderBase):
  def run(self, ct: Controller) -> None:
    # make sure we can afford a harvester, and not just wander around spamming conveyors
    # random is to make sure bots run later during the turn don't get entirely excluded by earlier bots using up the Titanium
    if ct.get_global_resources()[0] < ct.get_harvester_cost()[0] * (1 + random.random() / 4):
      return

    # move logic
    i = 0
    while True:
      builtForward = False
      movePos = ct.get_position().add(self.moveDir)

      # Check to see if suicide
      if random.random() < SUICIDE_BOT_CHANCE:
        self.builderImpl = SuicideBot()

      if self.tryBuildAdjacentHarvester(ct):
        # just made a harvester, can't make a conveyor to move onto
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
      elif self.posIsInbounds(ct, movePos) and ct.get_entity_type(ct.get_tile_building_id(movePos)) == EntityType.ROAD and ct.get_team(ct.get_tile_building_id(movePos)) == ct.get_team():
        ct.destroy(movePos)
        ct.build_conveyor(movePos, self.revDir)
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

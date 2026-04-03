

from cambc import Controller, Direction, EntityType, Environment, Position
import random

SPAWN_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]

class Core():
  def __init__(self):
    self.numSpawned = 0

  def startup(self, ct):
    #nothin
    return
  
  def run(self, ct: Controller):
    titanium = ct.get_global_resources()[0]
    harvesterCost = ct.get_harvester_cost()[0]
    botCost = ct.get_builder_bot_cost()[0]
    if (titanium < 950 and ct.get_current_round()%10 != 0) or titanium < botCost + harvesterCost:
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
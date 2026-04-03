

from cambc import Controller, Direction, EntityType, Environment, Position
import random, sys
from bot_roles.conveyor_bot import ConveyorBot
from bot_roles.suicide_bot import SuicideBot
from bot_roles.turretmaker_bot import TurretmakerBot

SUICIDE_BOT_CHANCE = 0.1

class Bot():
  def __new__(cls, ct: Controller):
    #if ct.get_current_round() > 50 or random.random() < SUICIDE_BOT_CHANCE:
    #  return SuicideBot()
    #elif random.random() < 0.5:
    #  return TurretmakerBot()
    return ConveyorBot()
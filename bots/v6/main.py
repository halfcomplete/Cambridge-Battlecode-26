

from cambc import Controller, Direction, EntityType, Environment, Position

from bot import Bot
from core import Core
from turrets import Turret
import pathfinding as pfind

class Player:
  def __init__(self):
    self.entityCode = None
    self.maxCpuCost = 0
    self.rollingAvCpuCost = 0

  def run(self, ct: Controller) -> None:
    if self.entityCode == None:
      self.entityCode = getEntityCode(ct)
      self.entityCode.startup(ct)

    self.entityCode.run(ct) #type: ignore

    cpuCost = ct.get_cpu_time_elapsed()
    if(cpuCost>self.maxCpuCost):
      self.maxCpuCost = cpuCost
    self.rollingAvCpuCost = (self.rollingAvCpuCost * 39 + cpuCost)/40
    print("av cpu: ",self.rollingAvCpuCost)
    print("max cpu: ",self.maxCpuCost)

def getEntityCode(ct: Controller):
  eType = ct.get_entity_type()
  match eType:
    case EntityType.BUILDER_BOT:
      return Bot(ct)
    case EntityType.CORE:
      return Core()
  return Turret(eType)
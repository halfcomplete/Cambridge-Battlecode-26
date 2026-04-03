# Pathfinding code for Cambridge Battlecode 2026
# Team Mind of Metal and Wheels
# Author: Telos, March 2026. Α⳩ω

# Goal is to get simple pathing up and running ASAP
# So will probably include several out of date functions as we iterate and upgrade.
# some of the later function contain copies of the earlier functions, violating DRY but saving cpu and if statements.

from cambc import Controller, Direction, EntityType, Environment, Position

OCT_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
QUAD_DIRECTIONS = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]

def getOctDirOfPos(fromPos: Position, toPos: Position) -> Direction:
  dx = toPos.x - fromPos.x
  dy = toPos.y - fromPos.y

  if dx == 0 and dy == 0:
    return Direction.CENTRE
  if abs(dx) > abs(dy) * 2:
    return Direction.EAST if dx > 0 else Direction.WEST
  if abs(dy) > abs(dx) * 2:
    return Direction.SOUTH if dy > 0 else Direction.NORTH
  if dx > 0:
    return Direction.SOUTHEAST if dy > 0 else Direction.NORTHEAST
  return Direction.SOUTHWEST if dy > 0 else Direction.NORTHWEST

def getQuadDirOfPos(fromPos: Position, toPos: Position) -> Direction:
  dx = toPos.x - fromPos.x
  dy = toPos.y - fromPos.y

  if dx == 0 and dy == 0:
    return Direction.CENTRE
  if abs(dx) > abs(dy):
    return Direction.EAST if dx > 0 else Direction.WEST
  return Direction.SOUTH if dy > 0 else Direction.NORTH

def getChebyshevDistance(fromPos: Position, toPos: Position) -> int:
  dx = abs(toPos.x - fromPos.x)
  dy = abs(toPos.y - fromPos.y)
  return max(dx, dy)

def getManhattanDistance(fromPos: Position, toPos: Position) -> int:
  dx = abs(toPos.x - fromPos.x)
  dy = abs(toPos.y - fromPos.y)
  return dx + dy

# !!!!
# IMPORTANT
# these pathfinding functions consider it a successful path to get NEXT TO the target, not on the target.
# so if you want to get ON the target, confirm it seperately!!
# !!!!

#TODO consider removing if dir = Direction.CENTRE case if need to save cpu
#TODO consider replacing all chebyshev distance checks with manhattan distance checks to get closer to target.

def unsafeQuadBlindGreedyPath(fromPos: Position, toPos: Position, ct: Controller) -> Direction | None:
  # returns a direction to move in to get from fromPos to toPos, or None if no path exists
  # unsafe - doesn't check the whole path, so can be easily blocked.
  # quad - only checks cardinal directions, good for conveyors.
  # blind - only checks one tile in the direction of the target ('touching distance')
  # greedy - don't consider alternate directions
  dir = getQuadDirOfPos(fromPos, toPos)
  targetPos = fromPos.add(dir)
  if ct.is_tile_passable(targetPos) or ct.is_tile_empty(targetPos):
    return dir
  if dir == Direction.CENTRE:
    return dir
  return None

def unsafeOctBlindGreedyPath(fromPos: Position, toPos: Position, ct: Controller) -> Direction | None:
  # returns a direction to move in to get from fromPos to toPos, or None if no path exists
  # unsafe - doesn't check the whole path, so can be easily blocked.
  # oct - checks all eight directions, good for general movement.
  # blind - only checks one tile in the direction of the target ('touching distance')
  # greedy - don't consider alternate directions
  dir = getOctDirOfPos(fromPos, toPos)
  targetPos = fromPos.add(dir)
  if ct.is_tile_passable(targetPos) or ct.is_tile_empty(targetPos):
    return dir
  if dir == Direction.CENTRE:
    return dir
  return None

def safeQuadBlindGreedyPath(fromPos: Position, toPos: Position, ct: Controller) -> Direction | None:
  # returns a direction to move in to get from fromPos to toPos, or None if no path exists
  # safe - only returns if entire path is found and clear, otherwise returns None
  # quad - only checks cardinal directions, good for conveyors.
  # blind - only checks one tile in the direction of the target ('touching distance')
  # greedy - don't consider alternate directions
  dir = getQuadDirOfPos(fromPos, toPos)
  targetPos = fromPos.add(dir)
  if getManhattanDistance(targetPos, toPos) == 1 and (ct.is_tile_passable(targetPos) or ct.is_tile_empty(targetPos)):
    return dir
  if dir == Direction.CENTRE:
    return dir
  return None

def safeOctBlindGreedyPath(fromPos: Position, toPos: Position, ct: Controller) -> Direction | None:
  # returns a direction to move in to get from fromPos to toPos, or None if no path exists
  # safe - only returns if entire path is found and clear, otherwise returns None
  # oct - checks all eight directions, good for general movement.
  # blind - only checks one tile in the direction of the target ('touching distance')
  # greedy - don't consider alternate directions
  dir = getOctDirOfPos(fromPos, toPos)
  targetPos = fromPos.add(dir)
  if getChebyshevDistance(targetPos, toPos) == 1 and (ct.is_tile_passable(targetPos) or ct.is_tile_empty(targetPos)):
    return dir
  if dir == Direction.CENTRE:
    return dir
  return None

def unsafeQuadBlindOpportunisticPath(fromPos: Position, toPos: Position, ct: Controller) -> Direction | None:
  # returns a direction to move in to get from fromPos to toPos, or None if no path exists
  # unsafe - doesn't check the whole path, so can be easily blocked.
  # quad - only checks cardinal directions, good for conveyors.
  # blind - only checks one tile in the direction of the target ('touching distance')
  # opportunistic - if the direct path is blocked, will check other directions for a path that gets closer to the target
  bestDir = getQuadDirOfPos(fromPos, toPos)
  targetPos = fromPos.add(bestDir)
  if ct.is_tile_passable(targetPos) or ct.is_tile_empty(targetPos):
    return bestDir
  if bestDir == Direction.CENTRE:
    return bestDir

  # check other directions for an opportunistic path
  firstDir = bestDir
  bestDir = None
  bestDist = getManhattanDistance(fromPos, toPos)

  #try 90 degrees rightward
  testDir = firstDir.rotate_right().rotate_right()
  testPos = fromPos.add(testDir)
  testDist = getManhattanDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist
  #try 90 degrees leftward
  testDir = firstDir.rotate_left().rotate_left()
  testPos = fromPos.add(testDir)
  testDist = getManhattanDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist

  return bestDir

def unsafeOctBlindOpportunisticPath(fromPos: Position, toPos: Position, ct: Controller) -> Direction | None:
  # returns a direction to move in to get from fromPos to toPos, or None if no path exists
  # unsafe - doesn't check the whole path, so can be easily blocked.
  # oct - checks all eight directions, good for general movement.
  # blind - only checks one tile in the direction of the target ('touching distance')
  # opportunistic - if the direct path is blocked, will check other directions for a path that gets closer to the target
  bestDir = getOctDirOfPos(fromPos, toPos)
  targetPos = fromPos.add(bestDir)
  if ct.is_tile_passable(targetPos) or ct.is_tile_empty(targetPos):
    return bestDir
  if bestDir == Direction.CENTRE:
    return bestDir

  # check other directions for an opportunistic path
  firstDir = bestDir
  bestDir = None
  bestDist = getChebyshevDistance(fromPos, toPos)

  #try 45 degrees rightward
  testDir = firstDir.rotate_right()
  testPos = fromPos.add(testDir)
  testDist = getChebyshevDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist
  #try 90 degrees rightward
  testDir = testDir.rotate_right()
  testPos = fromPos.add(testDir)
  testDist = getChebyshevDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist
  #try 45 degrees leftward
  testDir = firstDir.rotate_left()
  testPos = fromPos.add(testDir)
  testDist = getChebyshevDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist
  #try 90 degrees leftward
  testDir = testDir.rotate_left()
  testPos = fromPos.add(testDir)
  testDist = getChebyshevDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist

  return bestDir

def safeQuadBlindOpportunisticPath(fromPos: Position, toPos: Position, ct: Controller) -> Direction | None:
  # returns a direction to move in to get from fromPos to toPos, or None if no path exists
  # safe - only returns if entire path is found and clear, otherwise returns None
  # quad - only checks cardinal directions, good for conveyors.
  # blind - only checks one tile in the direction of the target ('touching distance')
  # opportunistic - if the direct path is blocked, will check other directions for a path that gets closer to the target
  bestDir = getQuadDirOfPos(fromPos, toPos)
  targetPos = fromPos.add(bestDir)
  if getManhattanDistance(targetPos, toPos) == 1 and (ct.is_tile_passable(targetPos) or ct.is_tile_empty(targetPos)):
    return bestDir
  if bestDir == Direction.CENTRE:
    return bestDir

  # check other directions for an opportunistic path
  firstDir = bestDir
  bestDir = None
  bestDist = getManhattanDistance(fromPos, toPos)

  #try 90 degrees rightward
  testDir = firstDir.rotate_right().rotate_right()
  testPos = fromPos.add(testDir)
  testDist = getManhattanDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist
  #try 90 degrees leftward
  testDir = firstDir.rotate_left().rotate_left()
  testPos = fromPos.add(testDir)
  testDist = getManhattanDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist

  if(bestDist == 1):
    return bestDir
  return None

def safeOctBlindOpportunisticPath(fromPos: Position, toPos: Position, ct: Controller) -> Direction | None:
  # returns a direction to move in to get from fromPos to toPos, or None if no path exists
  # safe - only returns if entire path is found and clear, otherwise returns None
  # oct - checks all eight directions, good for general movement.
  # blind - only checks one tile in the direction of the target ('touching distance')
  # opportunistic - if the direct path is blocked, will check other directions for a path that gets closer to the target
  bestDir = getOctDirOfPos(fromPos, toPos)
  targetPos = fromPos.add(bestDir)
  if getChebyshevDistance(targetPos, toPos) == 1 and (ct.is_tile_passable(targetPos) or ct.is_tile_empty(targetPos)):
    return bestDir
  if bestDir == Direction.CENTRE:
    return bestDir

  # check other directions for an opportunistic path
  firstDir = bestDir
  bestDir = None
  bestDist = getChebyshevDistance(fromPos, toPos)

  #try 45 degrees rightward
  testDir = firstDir.rotate_right()
  testPos = fromPos.add(testDir)
  testDist = getChebyshevDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist
  #try 90 degrees rightward
  testDir = testDir.rotate_right() #chains off the 45, will break if reorganized
  testPos = fromPos.add(testDir)
  testDist = getChebyshevDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist
  #try 45 degrees leftward
  testDir = firstDir.rotate_left()
  testPos = fromPos.add(testDir)
  testDist = getChebyshevDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist
  #try 90 degrees leftward
  testDir = testDir.rotate_left() #chains off the 45, will break if reorganized
  testPos = fromPos.add(testDir)
  testDist = getChebyshevDistance(testPos, toPos)
  if testDist < bestDist and (ct.is_tile_passable(testPos) or ct.is_tile_empty(testPos)):
    bestDir = testDir
    bestDist = testDist

  if(bestDist == 1):
    return bestDir
  return None
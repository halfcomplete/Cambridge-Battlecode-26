
# Goal is to get simple pathing up and running ASAP


from cambc import Controller, Direction, EntityType, Environment, Position

OCT_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
QUAD_DIRECTIONS = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]

def getDirOfPos(fromPos: Position, toPos: Position) -> Direction:
  dx = toPos.x - fromPos.x
  dy = toPos.y - fromPos.y

  if dx == 0 and dy == 0:
    return Direction.CENTRE
  if abs(dx) > abs(dy) * 2:
    return Direction.EAST if dx > 0 else Direction.WEST
  if abs(dy) > abs(dx) * 2:
    return Direction.SOUTH if dy > 0 else Direction.NORTH
  if dx > 0:
    return Direction.SOUTH_EAST if dy > 0 else Direction.NORTH_EAST
  return Direction.SOUTH_WEST if dy > 0 else Direction.NORTH_WEST

def blindGreedyPath(fromPos: Position, toPos: Position, ct: Controller) -> Direction:
  # returns a direction to move in to get from fromPos to toPos, or None if no path exists
  # only checks one tile in the direction of the target, so may return a direction that is blocked by an obstacle
  dir = getDirOfPos(fromPos, toPos)
  targetPos = fromPos.add(dir)
  if ct.is_tile_passable(targetPos) or ct.is_tile_empty(targetPos):
    return dir
  return Direction.CENTRE
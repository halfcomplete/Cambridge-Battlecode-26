
import random
from cambc import Controller, Direction, EntityType, Position
from bot_roles.builder_base import BuilderBase
import pathfinding as pfind

SPAWN_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
STUBBORNNESS = 0.1

class SuicideBot(BuilderBase):
	def __init__(self):
		super().__init__()
		self.moveDir = random.choice(SPAWN_DIRECTIONS)
		self.detonate = random.random() < 0.05
		self.roleColor = [150,0,0] if not self.detonate else [255,0,0]
		self.justSpawned = True
		self.coreLocation = None
		self.possibleEnemyCorePositions = []
		self.suicideBotType = random.random()

	def run(self, ct: Controller) -> None:
		pos = ct.get_position()
		ct.draw_indicator_dot(pos, *self.roleColor)

		if self.justSpawned == True:
			nearby_tiles = ct.get_nearby_tiles()
			for nearbyPos in nearby_tiles:
				nearbyBuilding = ct.get_tile_building_id(nearbyPos)
				nearbyEntity = ct.get_entity_type(nearbyBuilding)
				if nearbyPos is None or nearbyEntity == EntityType.CORE:
					self.coreLocation = nearbyPos
					self.justSpawned = False
					break
		self.possibleEnemyCorePositions = self.getPossibleEnemyPositions(ct)

		# --- Step 1: Follow conveyor beneath ---
		tileUnderneath = ct.get_tile_building_id(pos)
		if tileUnderneath is not None:
			if ct.get_entity_type(tileUnderneath) == (EntityType.CONVEYOR or EntityType.BRIDGE):
				if ct.get_team(tileUnderneath) != ct.get_team():
					# Random chance set at start to destroy first enemy structure
					if self.suicideBotType < 0.2: 
						ct.self_destruct()
					conveyorDir = ct.get_direction(tileUnderneath)
					self.moveDir = conveyorDir
			if ct.get_entity_type(tileUnderneath) == EntityType.ROAD and self.getDistanceFromCore(ct) < 10 and self.suicideBotType < 0.8:
				ct.self_destruct()
		# --- Step 2: Check nearby tiles for enemy core ---
		nearby_tiles = ct.get_nearby_tiles()
		for nearbyPos in nearby_tiles:
			nearbyPos = ct.get_tile_building_id(nearbyPos)
			if nearbyPos is None or ct.get_entity_type(nearbyPos) != EntityType.CORE:
				continue
			if ct.get_team(nearbyPos) != ct.get_team():
				self.detonate = True
				self.roleColor = [255,0,0]
				break 
		#slight duplicate of the above, but this looks only at the core
		for potentialPos in self.possibleEnemyCorePositions:
			if potentialPos not in nearby_tiles:
				continue
			building = ct.get_tile_building_id(potentialPos)
			if(building == None):
				self.possibleEnemyCorePositions.remove(potentialPos)
				break
			if( ct.get_entity_type(building)==EntityType.CORE and ct.get_team()!=ct.get_team(building)):
				self.possibleEnemyCorePositions = [potentialPos]
		
		#kablooey
		if self.detonate and ct.get_team(tileUnderneath) != ct.get_team():
			ct.self_destruct()
			return
		
		#scan for nearby enemy
		if (self.detonate or random.random()<STUBBORNNESS) and ct.get_team(tileUnderneath) == ct.get_team():
			visibleTiles = ct.get_nearby_tiles()
			random.shuffle(visibleTiles)
			for tile in visibleTiles:
				buildingId = ct.get_tile_building_id(tile)
				if ct.get_team() == ct.get_team(buildingId) or ct.get_entity_type(buildingId) not in [EntityType.ROAD, EntityType.CONVEYOR]:
					continue
				testDir = pfind.safeOctBlindOpportunisticPath(pos, tile, ct)
				if testDir == None:
					continue
				self.moveDir = testDir
				break

		# --- Step 3: Move along conveyor ---
		if random.random() < 0.05:
			# Occasionally change direction to avoid getting stuck
			self.moveDir = pos.direction_to(random.choice(self.possibleEnemyCorePositions))

		nextPos = pos.add(self.moveDir)
		if ct.can_build_road(nextPos):
			#building roads can drain our resources if we aren't careful.
			if ct.get_global_resources()[0] < ct.get_harvester_cost()[0] * (1 + random.random() / 4):
				return
			ct.build_road(nextPos)

		if ct.can_move(self.moveDir):
			ct.move(self.moveDir)
		else:
			#if it's not shuffled, prefers to go north/east over all other directions.
			randomDirections = [d for d in Direction]
			random.shuffle(randomDirections)
			# If blocked, pick any valid direction (preferably towards conveyors)
			for d in randomDirections:
				if d != Direction.CENTRE and ct.can_move(d):
					self.moveDir = d
					ct.move(d)
					break

	def getPossibleEnemyPositions(self, ct: Controller):
		possiblePositions = []
		width = ct.get_map_width()
		height = ct.get_map_height()

		x1 = -self.coreLocation.x + width#type: ignore
		y1 = self.coreLocation.y#type: ignore

		x2 = self.coreLocation.x#type: ignore
		y2 = -self.coreLocation.y + height#type: ignore

		x3 = -self.coreLocation.x + width#type: ignore
		y3 = -self.coreLocation.y + height#type: ignore

		possiblePositions.append(Position(x1, y1)) 
		possiblePositions.append(Position(x2, y2)) 
		possiblePositions.append(Position(x3, y3)) 
		return possiblePositions
	
	def getDistanceFromCore(self, ct: Controller):
		pos = ct.get_position()
		x = abs(self.coreLocation.x - pos.x) #type: ignore
		y = abs(self.coreLocation.y - pos.y) #type: ignore
		return x if x < y else y
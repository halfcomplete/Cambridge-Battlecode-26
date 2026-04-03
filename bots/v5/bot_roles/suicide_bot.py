

import random
from cambc import Controller, Direction, EntityType, GameError
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

	def run(self, ct: Controller) -> None:
		pos = ct.get_position()
		ct.draw_indicator_dot(pos, *self.roleColor)

		# --- Step 1: Follow conveyor beneath ---
		tileUnderneath = ct.get_tile_building_id(pos)
		if tileUnderneath is not None and ct.get_entity_type(tileUnderneath) == EntityType.CONVEYOR:
			if ct.get_team(tileUnderneath) != ct.get_team():
				conveyorDir = ct.get_direction(tileUnderneath)
				self.moveDir = conveyorDir

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
			self.moveDir = random.choice(SPAWN_DIRECTIONS)

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
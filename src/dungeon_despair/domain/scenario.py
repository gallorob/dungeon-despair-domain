from enum import Enum, auto

from dungeon_despair.domain.level import Level


class ScenarioType(Enum):
	EXPLORE = auto()
	TREAURE_HUNT = auto()
	BOSS_FIGHT = auto()
	

def check_level_playability(level: Level,
                            condition: ScenarioType) -> bool:
	if condition == ScenarioType.EXPLORE:
		# Current room must always be a room
		assert level.current_room in level.rooms.keys(), f'Current room must be a room and not a corridor (currently: {level.current_room}).'
		# Explore mission require at least three rooms
		assert len(level.rooms) >= 3, f'Explore missions should have at least 3 rooms; found: {len(level.rooms)}.'
		# Check all enemies have at least 1 attack
		for room in level.rooms.values():
			for enemy in room.encounter.entities['enemy']:
				assert len(enemy.attacks) > 0, f'Enemies must all have at least one attack: {enemy.name} in {room.name} has {len(enemy.attacks)} attacks.'
		for corridor in level.corridors.values():
			for encounter in corridor.encounters:
				for enemy in encounter.entities['enemy']:
					assert len(enemy.attacks) > 0, f'Enemies must all have at least one attack: {enemy.name} in {room.name} has {len(enemy.attacks)} attacks.'
		# other checks...?
		
	elif condition == ScenarioType.TREAURE_HUNT:
		raise NotImplementedError('Treasure Hunts scenarios have not been implemented yet!')
	elif condition == ScenarioType.BOSS_FIGHT:
		raise NotImplementedError('Boss fight scenarios have not been implemented yet!')
	else:
		raise ValueError(f'Invalid condition: {condition}')
	
	return True
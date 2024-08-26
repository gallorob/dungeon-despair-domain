from enum import Enum, auto
from typing import Dict

from dungeon_despair.domain.configs import config
from dungeon_despair.domain.entities.enemy import Enemy
from dungeon_despair.domain.entities.trap import Trap
from dungeon_despair.domain.entities.treasure import Treasure


class Direction(Enum):
	NORTH = 'north'
	SOUTH = 'south'
	EAST = 'east'
	WEST = 'west'
	

class EntityEnum(Enum):
	ENEMY = 'enemy'
	TRAP = 'trap'
	TREASURE = 'treasure'


opposite_direction: Dict[Direction, Direction] = {
	Direction.NORTH: Direction.SOUTH,
	Direction.SOUTH: Direction.NORTH,
	Direction.EAST: Direction.WEST,
	Direction.WEST: Direction.EAST,
}

entityclass_thresolds: Dict[EntityEnum, int] = {
	EntityEnum.ENEMY:    config.max_enemies_per_encounter,
	EntityEnum.TRAP:     config.max_traps_per_encounter,
	EntityEnum.TREASURE: config.max_treasures_per_encounter
}


def get_enum_by_value(enum_class,
                      value):
	try:
		return enum_class(value)
	except ValueError:
		return None


# TODO: Add functions to create/derive/check corridor names
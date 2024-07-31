from enum import Enum, auto

from dungeon_despair.domain.configs import config
from dungeon_despair.domain.entities.enemy import Enemy
from dungeon_despair.domain.entities.trap import Trap
from dungeon_despair.domain.entities.treasure import Treasure


class Direction(Enum):
	NORTH = auto()
	SOUTH = auto()
	EAST = auto()
	WEST = auto()
	

class EntityClass(Enum):
	ENEMY = Enemy
	TRAP = Trap
	TREASURE = Treasure


opposite_directions = {
	Direction.NORTH: Direction.SOUTH,
	Direction.SOUTH: Direction.NORTH,
	Direction.EAST: Direction.WEST,
	Direction.WEST: Direction.EAST,
}

entityclass_thresolds = {
	EntityClass.ENEMY:    config.max_enemies_per_encounter,
	EntityClass.TRAP:     config.max_traps_per_encounter,
	EntityClass.TREASURE: config.max_treasures_per_encounter
}
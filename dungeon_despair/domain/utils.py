from enum import Enum
from typing import Dict, List

from dungeon_despair.domain.configs import config


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
    EntityEnum.ENEMY: config.max_enemies_per_encounter,
    EntityEnum.TRAP: config.max_traps_per_encounter,
    EntityEnum.TREASURE: config.max_treasures_per_encounter
}


def get_enum_by_value(enum_class,
                      value):
    try:
        return enum_class(value)
    except ValueError:
        return None


def make_corridor_name(room_from_name: str,
                       room_to_name: str) -> str:
    return f'{room_from_name}-{room_to_name}'


def derive_rooms_from_corridor_name(corridor_name: str) -> List[str]:
    return corridor_name.split('-')


def is_corridor(name: str) -> bool:
    return len(derive_rooms_from_corridor_name(name)) == 2


def get_encounter(level: "Level",
                  room_name: str,
                  cell_index: int) -> "Encounter":
    if not is_corridor(room_name):
        room = level.rooms.get(room_name, None)
        assert room is not None, f'Room {room_name} does not exist.'
        return room.encounter
    else:
        corridor = level.get_corridor(*derive_rooms_from_corridor_name(room_name), ordered=False)
        assert corridor is not None, f'Corridor {room_name} does not exist.'
        assert 0 < cell_index <= corridor.length, f'{room_name} is a corridor, but cell_index={cell_index} is invalid, it should be a value between 1 and {corridor.length} (inclusive).'
        return corridor.encounters[cell_index - 1]

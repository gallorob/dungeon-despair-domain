from enum import Enum
from typing import Dict, List, Tuple

from dungeon_despair.domain.configs import config


class Direction(Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


ordered_directions = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]


opposite_direction: Dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
}


class EntityEnum(Enum):
    ENEMY = "enemy"
    TRAP = "trap"
    TREASURE = "treasure"


entityclass_thresolds: Dict[EntityEnum, int] = {
    EntityEnum.ENEMY: config.max_enemies_per_encounter,
    EntityEnum.TRAP: config.max_traps_per_encounter,
    EntityEnum.TREASURE: config.max_treasures_per_encounter,
}


class ActionType(Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    # Used only in-game

    PASS = "pass"
    MOVE = "move"


class ModifierType(Enum):
    BLEED = "bleed"
    HEAL = "heal"
    STUN = "stun"
    SCARE = "scare"


def get_enum_by_value(enum_class, value):
    try:
        return enum_class(value)
    except ValueError:
        return None


def make_corridor_name(room_from_name: str, room_to_name: str) -> str:
    return f"{room_from_name}-{room_to_name}"


def get_encounter(level: "Level", room_name: str, cell_index: int) -> "Encounter":
    assert (
        room_name in level.rooms.keys() or room_name in level.corridors.keys()
    ), f"{room_name} is not in the level."
    if room_name in level.rooms.keys():
        room = level.rooms[room_name]
        return room.encounter
    else:
        corridor = level.corridors[room_name]
        assert (
            0 < cell_index <= corridor.length
        ), f"{room_name} is a corridor, but cell_index={cell_index} is invalid, it should be a value between 1 and {corridor.length} (inclusive)."
        return corridor.encounters[cell_index - 1]


def get_new_coords(
    coords: Tuple[int, int], direction: Direction, n: int
) -> Tuple[int, int]:
    if direction == Direction.SOUTH:
        return (coords[0], coords[1] + n)
    elif direction == Direction.NORTH:
        return (coords[0], coords[1] - n)
    elif direction == Direction.EAST:
        return (coords[0] + n, coords[1])
    elif direction == Direction.WEST:
        return (coords[0] - n, coords[1])
    else:
        raise ValueError(f"Invalid direction {direction}")


def get_rotation(from_direction: Direction, to_direction: Direction):
    from_i = ordered_directions.index(from_direction)
    to_i = ordered_directions.index(to_direction)
    return to_i - from_i


def get_rotated_direction(direction: Direction, rotate_by: int) -> Direction:
    return ordered_directions[
        (ordered_directions.index(direction) + rotate_by) % len(ordered_directions)
    ]


def check_intersection_coords(
    coords: Tuple[int, int], level: "Level"
) -> Tuple[bool, str]:
    for room_name in level.rooms.keys():
        if coords == level.rooms[room_name].coords:
            return True, room_name
    for corridor_name in level.corridors.keys():
        if coords in level.corridors[corridor_name].coords:
            return True, corridor_name
    return False, ""


def check_if_in_loop(
    corridor: "Corridor", connections: Dict[str, Dict[Direction, str]]
) -> bool:
    room_from, room_to = corridor.room_from, corridor.room_to
    explored_rooms = []
    paths = [room_to]
    new_paths = []
    while len(paths) > 0:
        for room in paths:
            explored_rooms.append(room)
            for direction in Direction:
                connecting_room = connections[room][direction]
                if connecting_room != "":
                    if connecting_room == room_from:
                        if room != room_to:
                            return True
                    else:
                        if connecting_room not in explored_rooms:
                            new_paths.append(connecting_room)
        paths = new_paths
        new_paths = []
    return False


def set_entity_cost(entity: "Entity", entity_type: EntityEnum) -> None:
    if entity_type == EntityEnum.ENEMY:
        tot_dmg = sum(attack.base_dmg * attack.accuracy for attack in entity.attacks)
        entity.cost = int(entity.max_hp + tot_dmg)
    elif entity_type == EntityEnum.TRAP:
        entity.cost = entity.dmg * entity.chance
    elif entity_type == EntityEnum.TREASURE:
        entity.cost = entity.dmg * entity.trapped_chance
    else:
        raise ValueError(f"Invalid entity type: {entity_type}")

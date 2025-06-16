import copy
import json

from gptfunctionutil import AILibFunction, GPTFunctionLibrary, LibParam, LibParamSpec

from dungeon_despair.domain.attack import Attack
from dungeon_despair.domain.configs import config
from dungeon_despair.domain.corridor import Corridor
from dungeon_despair.domain.encounter import Encounter
from dungeon_despair.domain.entities.enemy import Enemy
from dungeon_despair.domain.entities.trap import Trap
from dungeon_despair.domain.entities.treasure import Treasure
from dungeon_despair.domain.level import Level

from dungeon_despair.domain.modifier import Modifier
from dungeon_despair.domain.room import Room
from dungeon_despair.domain.utils import (
    ActionType,
    check_if_in_loop,
    check_intersection_coords,
    Direction,
    EntityEnum,
    get_encounter,
    get_enum_by_value,
    get_new_coords,
    get_rotated_direction,
    get_rotation,
    make_corridor_name,
    ModifierType,
    opposite_direction,
)


class DungeonCrawlerFunctions(GPTFunctionLibrary):
    def try_call_func(self, func_name: str, func_args: str, level: Level) -> str:
        if isinstance(func_args, str):
            func_args = json.loads(func_args)
        try:
            operation_result = self.call_by_dict(
                {"name": func_name, "arguments": {"level": level, **func_args}}
            )
            return operation_result
        except AssertionError as e:
            return f"Domain validation error: {e}"
        except AttributeError as e:
            return f"Function {func_name} not found."
        except TypeError as e:
            return f"Missing arguments: {e}"

    @AILibFunction(
        name="add_room",
        description="Add a room to the level. If the level is not empty, a corridor will also be created between the new room and an existing room.",
        required=["name", "description", "room_from", "direction"],
    )
    @LibParam(name="The room name")
    @LibParam(description="The room physical characteristics")
    @LibParam(
        room_from='The existing room the new room connects from. If unspecified, set it to "" if there is no current room, otherwise set it to the current room.'
    )
    @LibParam(
        direction='The direction the new room connects from. If unspecified, set it to "" if there is no current room, otherwise set it to one of the available directions (either "north", "south", "east", or "west").'
    )
    def add_room(
        self, level: Level, name: str, description: str, room_from: str, direction: str
    ) -> str:
        assert name != "", f"Room name should be provided."
        assert description != "", f"Room description should be provided."
        assert (
            name not in level.rooms.keys()
        ), f"Could not add {name} to the level: {name} already exists."
        if level.current_room == "":
            assert (
                room_from == ""
            ), f"Could not add {name} to the level: room_from must not be set if there is no current room."
        if level.current_room != "":
            assert (
                room_from != ""
            ), f"Could not add {name} to the level: room_from must be set if there exists a current room (current room is {level.current_room})."
            assert (
                direction != ""
            ), f"Could not add {name} to the level: direction must be set if there exists a current room (current room is {level.current_room})."
        if room_from != "":
            assert (
                room_from not in level.corridors.keys()
            ), f"Could not add {name} to the level: Cannot add a room from a corridor, try adding the room from either the rooms connected by the corridor {level.current_room}."
            assert (
                room_from in level.rooms.keys()
            ), f"{room_from} is not a valid room name."
            dir_enum = get_enum_by_value(Direction, direction)
            assert (
                dir_enum is not None
            ), f"Could not add {name} to the level: {direction} is not a valid direction."
            assert (
                level.connections[room_from][dir_enum] == ""
            ), f"Could not add {name} to the level: {direction} of {room_from} there already exists a room ({level.connections[room_from][dir_enum]})."
            # try add corridor to connecting room

            n = len(level.get_corridors_by_room(name)) // 2
            # can only add corridor if the connecting room has at most 3 corridors already

            assert (
                n < 4
            ), f"Could not add {name} to the level: {room_from} has too many connections."
            from_coords = level.rooms[room_from].coords
            new_coords = get_new_coords(
                coords=from_coords, direction=dir_enum, n=config.corridor_min_length + 1
            )
            intersects, intersection_name = check_intersection_coords(
                coords=new_coords, level=level
            )
            if intersects:
                raise AssertionError(
                    f"Could not add {name} to the level: {name} would clash in {intersection_name}."
                )
            corridor_coords = [
                get_new_coords(coords=from_coords, direction=dir_enum, n=x)
                for x in range(1, config.corridor_min_length + 1)
            ]
            for corridor_coord in corridor_coords:
                intersects, intersection_name = check_intersection_coords(
                    coords=corridor_coord, level=level
                )
                if intersects:
                    raise AssertionError(
                        f"Could not add {name} to the level: corridor between {room_from} and {name} would clash in {intersection_name}."
                    )
            # add the new room to the level

            level.rooms[name] = Room(
                name=name, description=description, coords=new_coords
            )
            level.current_room = name
            corridor = Corridor(
                room_from=room_from,
                room_to=name,
                name=f"{room_from}-{name}",
                direction=dir_enum,
                coords=corridor_coords,
            )
            level.corridors[corridor.name] = corridor
            level.connections[name] = {direction: "" for direction in Direction}
            level.connections[room_from][dir_enum] = name
            level.connections[name][opposite_direction[dir_enum]] = room_from
            return f"Added {name} to the level."
        else:
            # add the new room to the level

            level.rooms[name] = Room(name=name, description=description)
            level.current_room = name
            level.connections[name] = {direction: "" for direction in Direction}
            return f"Added {name} to the level."

    @AILibFunction(
        name="remove_room",
        description="Remove the room from the level",
        required=["name"],
    )
    @LibParam(name="The room name")
    def remove_room(self, level: Level, name: str) -> str:
        assert (
            name in level.rooms.keys()
        ), f"Could not remove {name}: {name} is not in the level."
        assert name != "", "Room name should be provided."
        # remove room

        del level.rooms[name]
        del level.connections[name]
        # remove connections to deleted room

        for corridor in level.get_corridors_by_room(name):
            del level.corridors[corridor.name]
            # remove connections in "to" rooms

            for direction in Direction:
                if (
                    corridor.room_to in level.rooms.keys()
                    and level.connections[corridor.room_to][direction] == name
                ):
                    level.connections[corridor.room_to][direction] = ""
                    break
        level.current_room = list(level.rooms.keys())[0] if len(level.rooms) > 0 else ""
        # Remove "hanging" rooms as well

        level.remove_hanging_rooms()
        return f"{name} has been removed from the dungeon."

    @AILibFunction(
        name="update_room",
        description="Update the room name or description.",
        required=["room_reference_name", "name", "description"],
    )
    @LibParam(room_reference_name="The original room name")
    @LibParam(name="The room name")
    @LibParam(description="The room physical characteristics")
    def update_room(
        self, level: Level, room_reference_name: str, name: str, description: str
    ) -> str:
        assert (
            room_reference_name in level.rooms.keys()
        ), f"Could not update {room_reference_name}: {room_reference_name} is not in the level."
        assert (
            room_reference_name != ""
        ), "Parameter room_reference_name should be provided."
        assert name != "", "Room name should be provided."
        assert description != "", "Room description should be provided."
        if name != room_reference_name:
            assert (
                name not in level.rooms.keys()
            ), f"Could not update {room_reference_name}: {name} already exists in the level."
        # get the current room

        room = level.rooms[room_reference_name]
        # remove it from the list of rooms (since room name can change)

        del level.rooms[room_reference_name]
        # update the room

        room.name = name
        # different description -> sprite must be regenerated

        if room.description != description:
            room.sprite = None
            # entities in the room may be updated, so reset their sprites as well

            for k in room.encounter.entities.keys():
                for entity in room.encounter.entities[k]:
                    entity.sprite = None
        # check the corridor(s) as well

        for corridor in level.get_corridors_by_room(room_reference_name):
            if corridor.room_from == room_reference_name:
                del level.corridors[corridor.name]
                corridor.room_from = room.name
                corridor.name = f"{room.name}-{corridor.room_to}"
                corridor.sprites = (
                    [] if room.description != description else corridor.sprites
                )
                level.corridors[corridor.name] = corridor
            if corridor.room_to == room_reference_name:
                del level.corridors[corridor.name]
                corridor.room_to = room.name
                corridor.name = f"{corridor.room_from}-{room.name}"
                corridor.sprites = (
                    [] if room.description != description else corridor.sprites
                )
                level.corridors[corridor.name] = corridor
        room.description = description
        # add room back

        level.rooms[name] = room
        # update level geometry

        room_connections = level.connections[room_reference_name]
        del level.connections[room_reference_name]
        level.connections[name] = room_connections
        for direction, other_room_name in level.connections[name].items():
            if other_room_name != "":
                level.connections[other_room_name][opposite_direction[direction]] = name
        if level.current_room == room_reference_name:
            level.current_room = name
        return f"Updated {room_reference_name}."

    @AILibFunction(
        name="add_corridor",
        description="Add a corridor between two existing rooms.",
        required=["room_from_name", "room_to_name", "corridor_length"],
    )
    @LibParam(room_from_name="The starting room name")
    @LibParam(room_to_name="The connecting room name")
    @LibParamSpec(
        name="corridor_length",
        description=f"The corridor length, must be a value must be between {config.corridor_min_length} and {config.corridor_max_length}.",
    )
    @LibParam(
        direction='The direction of the corridor from room_from_name to room_to_name. Must be one of "north", "south", "east", or "west".'
    )
    def add_corridor(
        self,
        level: Level,
        room_from_name: str,
        room_to_name: str,
        corridor_length: int,
        direction: str,
    ) -> str:
        assert room_from_name != "", f"room_from_name cannot be empty."
        assert room_to_name != "", f"room_to_name cannot be empty."
        assert (
            room_from_name != room_to_name
        ), f"{room_from_name} cannot be the same as {room_to_name}."
        assert (
            room_from_name in level.rooms.keys()
        ), f"Room {room_from_name} is not in the level."
        assert (
            room_to_name in level.rooms.keys()
        ), f"Room {room_to_name} is not in the level."
        corridor = level.corridors.get(
            make_corridor_name(room_from_name, room_to_name),
            level.corridors.get(make_corridor_name(room_to_name, room_from_name), None),
        )
        assert (
            corridor is None
        ), f"Could not add corridor: a corridor between {room_from_name} and {room_to_name} already exists."
        assert (
            config.corridor_min_length <= corridor_length <= config.corridor_max_length
        ), f"Could not add corridor: corridor_length should be between {config.corridor_min_length} and {config.corridor_max_length}, not {corridor_length}"
        dir_enum = get_enum_by_value(Direction, direction)
        assert (
            dir_enum is not None
        ), f"Could not add a corridor: {direction} is not a valid direction."
        assert (
            level.connections[room_from_name][dir_enum] == ""
        ), f"Could not add corridor: {direction} of {room_from_name} already has a corridor to {level.connections[room_from_name][dir_enum]}."
        n = (
            len(level.get_corridors_by_room(room_from_name)) // 2,
            len(level.get_corridors_by_room(room_to_name)) // 2,
        )  # number of corridors for each room
        # only add corridor if each room has at most 3 corridors

        assert (
            n[0] < 4
        ), f"Could not add corridor: {room_from_name} has already 4 connections."
        assert (
            n[1] < 4
        ), f"Could not add corridor: {room_to_name} has already 4 connections."
        # Check if the rooms are reachable with the specified corridor

        from_coords = level.rooms[room_from_name].coords
        to_coords = level.rooms[room_to_name].coords
        hyp_to_coords = get_new_coords(
            coords=from_coords, direction=dir_enum, n=corridor_length + 1
        )
        assert (
            to_coords == hyp_to_coords
        ), f"Could not add corridor: cannot reach {room_to_name} from {room_from_name} with a corridor of length {corridor_length} along {direction}."
        # Check if the corridor doesn't intersect other rooms/corridors

        corridor_coords = [
            get_new_coords(coords=from_coords, direction=dir_enum, n=x)
            for x in range(1, corridor_length + 1)
        ]
        for corridor_coord in corridor_coords:
            intersects, intersection_name = check_intersection_coords(
                coords=corridor_coord, level=level
            )
            if intersects:
                raise AssertionError(
                    f"Could not add corridor between {room_from_name} and {room_to_name} to the level: it would clash in {intersection_name}."
                )
        # Update level and add the corridor

        level.connections[room_from_name][dir_enum] = room_to_name
        level.connections[room_to_name][opposite_direction[dir_enum]] = room_from_name
        corridor = Corridor(
            room_from=room_from_name,
            room_to=room_to_name,
            name=make_corridor_name(room_from_name, room_to_name),
            length=corridor_length,
            encounters=[Encounter() for _ in range(corridor_length)],
            direction=dir_enum,
            coords=corridor_coords,
        )
        level.corridors[corridor.name] = corridor
        level.current_room = f"{room_from_name}-{room_to_name}"
        return f"Added corridor between {room_from_name} and {room_to_name}."

    @AILibFunction(
        name="remove_corridor",
        description="Remove a corridor",
        required=["room_from_name", "room_to_name"],
    )
    @LibParam(room_from_name="The starting room name")
    @LibParam(room_to_name="The connecting room name")
    def remove_corridor(
        self, level: Level, room_from_name: str, room_to_name: str
    ) -> str:
        assert room_from_name != "", f"room_from_name cannot be empty."
        assert room_to_name != "", f"room_to_name cannot be empty."
        corridor = level.corridors.get(
            make_corridor_name(room_from_name, room_to_name),
            level.corridors.get(make_corridor_name(room_to_name, room_from_name), None),
        )
        assert (
            corridor is not None
        ), f"Corridor between {room_from_name} and {room_to_name} does not exist."
        # remove the corridor from the level

        del level.corridors[corridor.name]
        # remove connection between the two rooms

        for room_a, room_b in [
            (room_from_name, room_to_name),
            (room_to_name, room_from_name),
        ]:
            for direction in Direction:
                if level.connections[room_a][direction] == room_b:
                    level.connections[room_a][direction] = ""
                    break
        # update the current room if necessary

        if level.current_room == corridor.name:
            level.current_room = corridor.room_from
        # Remove "hanging" rooms as well

        level.remove_hanging_rooms()
        return f"Removed corridor between {room_from_name} and {room_to_name}."

    @AILibFunction(
        name="update_corridor",
        description="Update a corridor. This can change the corridor's length, direction, and the rooms it connects to. Use this function to also change where a room is connected to.",
        required=[
            "room_from_reference_name",
            "room_to_reference_name",
            "room_from_name",
            "room_to_name",
            "corridor_length",
            "direction",
        ],
    )
    @LibParam(room_from_reference_name="The starting room name")
    @LibParam(room_to_reference_name="The connecting room name")
    @LibParam(room_from_name="The updated starting room name")
    @LibParam(room_to_name="The updated connecting room name")
    @LibParamSpec(
        name="corridor_length",
        description=f"The corridor length. Must be a value between {config.corridor_min_length} and {config.corridor_max_length}",
    )
    @LibParam(
        direction='The direction of the corridor from room_from_name to room_to_name. Must be one of "north", "south", "east", or "west".'
    )
    def update_corridor(
        self,
        level: Level,
        room_from_reference_name: str,
        room_to_reference_name: str,
        room_from_name: str,
        room_to_name: str,
        corridor_length: int,
        direction: str,
    ) -> str:
        assert (
            room_from_reference_name != ""
        ), f"room_from_reference_name cannot be empty."
        assert room_to_reference_name != "", f"room_to_reference_name cannot be empty."
        assert room_from_name != "", f"room_from_name cannot be empty."
        assert room_to_name != "", f"room_to_name cannot be empty."
        assert (
            config.corridor_min_length <= corridor_length <= config.corridor_max_length
        ), f"Could not add corridor: corridor_length should be between {config.corridor_min_length} and {config.corridor_max_length}, not {corridor_length}"

        ref_corridor = level.corridors.get(
            make_corridor_name(room_from_reference_name, room_to_reference_name),
            level.corridors.get(
                make_corridor_name(room_to_reference_name, room_from_reference_name),
                None,
            ),
        )
        assert (
            ref_corridor is not None
        ), f"Corridor between {room_from_reference_name} and {room_to_reference_name} does not exist."

        dir_enum = get_enum_by_value(Direction, direction)
        assert (
            dir_enum is not None
        ), f"Could not update corridor between {room_from_reference_name} and {room_to_reference_name}: {direction} is not a valid direction."

        # corridors cannot be changed if in a loop

        assert not check_if_in_loop(
            corridor=ref_corridor, connections=level.connections
        ), "Could not update corridor: corridors in a closed loop cannot be altered."

        # check a new corridor can be created if we're changing where it's connected to

        if room_from_reference_name != room_from_name:
            assert (
                level.connections[room_from_name][dir_enum] == ""
            ), f"Could not update corridor between {room_from_reference_name} and {room_to_reference_name}: {room_from_name} already has a corridor on {dir_enum.value}."
        if room_to_reference_name != room_to_name:
            assert (
                level.connections[room_to_name][opposite_direction[dir_enum]] == ""
            ), f"Could not update corridor between {room_from_reference_name} and {room_to_reference_name}: {room_to_name} already has a corridor on {opposite_direction[dir_enum].value}."
        # make a copy of the level

        level_copy = copy.deepcopy(level)
        # remove the old corridor

        level_copy.corridors.pop(ref_corridor.name)
        level_copy.connections[room_from_reference_name][
            get_enum_by_value(Direction, ref_corridor.direction)
        ] = ""
        level_copy.connections[room_to_reference_name][
            opposite_direction[get_enum_by_value(Direction, ref_corridor.direction)]
        ] = ""
        # create the new corridor

        new_corridor = Corridor(
            room_from=room_from_name,
            room_to=room_to_name,
            name=make_corridor_name(room_from_name, room_to_name),
            length=corridor_length,
            encounters=ref_corridor.encounters,
            direction=dir_enum,
            coords=[
                get_new_coords(
                    coords=level_copy.rooms[room_from_name].coords,
                    direction=dir_enum,
                    n=x,
                )
                for x in range(1, corridor_length + 1)
            ],
        )
        new_corridor.sprites = ref_corridor.sprites
        # Update encounters and sprites if the length of the corridor has changed

        if len(new_corridor.encounters) != new_corridor.length:
            if len(new_corridor.encounters) > new_corridor.length:
                # Drop extra encounters

                new_corridor.encounters = new_corridor.encounters[: new_corridor.length]
                # Drop extra sprites

                last_sprite = new_corridor.sprites[-1]  # Last sprite is kept
                new_corridor.sprites = new_corridor.sprites[
                    0 : new_corridor.length + 1
                ] + [last_sprite]
            else:
                while len(new_corridor.encounters) < new_corridor.length:
                    # Add new, empty encounters

                    new_corridor.encounters.append(Encounter())
                    # Add empty sprite

                    new_corridor.sprites.insert(-2, None)
        if (
            room_from_reference_name != room_from_name
            or room_to_reference_name != room_to_name
        ):
            new_corridor.sprites = []
        # Rotate room_from connections and subsequent corridors if the direction is different

        if get_enum_by_value(Direction, ref_corridor.direction) != dir_enum:
            rotation = get_rotation(
                from_direction=get_enum_by_value(Direction, ref_corridor.direction),
                to_direction=dir_enum,
            )
            _, connected_corridors = level_copy.get_level_subset(corridor=ref_corridor)
            rotated_rooms = []
            for connected_corridor in connected_corridors:
                connected_corridor.direction = get_rotated_direction(
                    get_enum_by_value(Direction, connected_corridor.direction), rotation
                )
                if connected_corridor.room_to not in rotated_rooms:
                    rotated_rooms.append(connected_corridor.room_to)
                    connections_copy = copy.deepcopy(
                        level_copy.connections[connected_corridor.room_to]
                    )
                    level_copy.connections[connected_corridor.room_to] = {
                        k: "" for k in Direction
                    }
                    for direction in Direction:
                        level_copy.connections[connected_corridor.room_to][
                            get_rotated_direction(
                                get_enum_by_value(Direction, direction), rotation
                            )
                        ] = connections_copy[direction]
            rotation = get_rotation(
                from_direction=get_enum_by_value(Direction, ref_corridor.direction),
                to_direction=dir_enum,
            )
            connections_copy = copy.deepcopy(
                level_copy.connections[ref_corridor.room_to]
            )
            level_copy.connections[ref_corridor.room_to] = {k: "" for k in Direction}
            for direction in Direction:
                level_copy.connections[ref_corridor.room_to][
                    get_rotated_direction(
                        get_enum_by_value(Direction, direction), rotation
                    )
                ] = connections_copy[direction]
        # Add new corridor to the level copy

        level_copy.corridors[new_corridor.name] = new_corridor
        level_copy.connections[room_from_name][dir_enum] = room_to_name
        level_copy.connections[room_to_name][
            opposite_direction[dir_enum]
        ] = room_from_name

        # Remove "hanging" rooms

        level_copy.remove_hanging_rooms(ref_room=room_from_name)
        # Update all coordinates--we assume room_from is "fixed"

        updating_rooms = [new_corridor.room_to]
        while len(updating_rooms) > 0:
            for room_name in updating_rooms:
                room = level_copy.rooms[room_name]
                connecting_corridors = level_copy.get_corridors_by_room(room_name)
                if len(connecting_corridors) > 0:
                    try:
                        connecting_corridor = connecting_corridors[
                            [c.room_to for c in connecting_corridors].index(room_name)
                        ]
                        room_from = level_copy.rooms[connecting_corridor.room_from]
                        room.coords = get_new_coords(
                            coords=room_from.coords,
                            direction=get_enum_by_value(
                                Direction, connecting_corridor.direction
                            ),
                            n=connecting_corridor.length + 1,
                        )
                        for other_corridor in connecting_corridors:
                            if other_corridor.room_from == room.name:
                                other_corridor.coords = [
                                    get_new_coords(
                                        coords=room.coords,
                                        direction=get_enum_by_value(
                                            Direction, other_corridor.direction
                                        ),
                                        n=x,
                                    )
                                    for x in range(1, other_corridor.length + 1)
                                ]
                    except ValueError as e:
                        print(
                            f"dungeon_despair.functions.update_corridor: ValueError {e}"
                        )
                updating_rooms.remove(room_name)
        # Check if any coordinates intersect

        for room in level_copy.rooms.values():
            for other_room in level_copy.rooms.values():
                if room.name != other_room.name and room.coords == other_room.coords:
                    raise AssertionError(
                        f"Could not update corridor between {room_from_reference_name} and {room_to_reference_name}: updated corridor would results in {room.name} intersect with {other_room.name}"
                    )
            for corridor in level_copy.corridors.values():
                if room.coords in corridor.coords:
                    raise AssertionError(
                        f"Could not update corridor between {room_from_reference_name} and {room_to_reference_name}: updated corridor would results in {room.name} intersect with {corridor.name}"
                    )
        level.rooms = level_copy.rooms
        level.corridors = level_copy.corridors
        level.connections = level_copy.connections
        level.current_room = new_corridor.name
        return f"Updated corridor between {room_from_name} and {room_to_name}."

    @AILibFunction(
        name="add_enemy",
        description="Add an enemy to a room or corridor.",
        required=[
            "room_name",
            "cell_index",
            "name",
            "description",
            "species",
            "hp",
            "dodge",
            "prot",
            "spd",
        ],
    )
    @LibParam(room_name="The room (or corridor) name")
    @LibParamSpec(
        name="cell_index",
        description="The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor.",
    )
    @LibParamSpec(name="name", description="The unique name of the enemy")
    @LibParamSpec(
        name="description", description="The physical description of the enemy"
    )
    @LibParamSpec(name="species", description="The species of the enemy")
    @LibParamSpec(
        name="hp",
        description=f"The health points of the enemy, must be a value must be between {config.min_hp} and {config.max_hp}.",
    )
    @LibParamSpec(
        name="dodge",
        description=f"The dodge points of the enemy, must be a value must be between {config.min_dodge} and {config.max_dodge}.",
    )
    @LibParamSpec(
        name="prot",
        description=f"The protection points of the enemy, must be a value must be between {config.min_prot} and {config.max_prot}.",
    )
    @LibParamSpec(
        name="spd",
        description=f"The speed points of the enemy, must be a value must be between {config.min_spd} and {config.max_spd}.",
    )
    def add_enemy(
        self,
        level: Level,
        room_name: str,
        name: str,
        description: str,
        species: str,
        hp: float,
        dodge: float,
        prot: float,
        spd: float,
        cell_index: int,
    ) -> str:
        assert room_name != "", "Parameter room_name should be provided."
        assert name != "", "Enemy name should be provided."
        assert description != "", "Enemy description should be provided."
        assert species != "", "Enemy species should be provided."
        assert (
            config.min_hp <= hp <= config.max_hp
        ), f"Invalid hp value: {hp}; should be between {config.min_hp} and  {config.max_hp}."
        assert (
            config.min_dodge <= dodge <= config.max_dodge
        ), f"Invalid dodge value: {dodge}; should be between {config.min_dodge} and  {config.max_dodge}."
        assert (
            config.min_prot <= prot <= config.max_prot
        ), f"Invalid prot value: {prot}; should be between {config.min_prot} and  {config.max_prot}."
        assert (
            config.min_spd <= spd <= config.max_spd
        ), f"Invalid spd value: {spd}; should be between {config.min_spd} and  {config.max_spd}."
        encounter = get_encounter(level, room_name, cell_index)
        assert name not in [
            enemy.name for enemy in encounter.entities[EntityEnum.ENEMY.value]
        ], f'Could not add enemy: {name} already exists in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
        assert (
            len(encounter.entities.get(EntityEnum.ENEMY.value, []))
            < config.max_enemies_per_encounter
        ), f'Could not add enemy: there are already {config.max_enemies_per_encounter} enemy(es) in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}, which is the maximum number allowed.'
        enemy = Enemy(
            name=name,
            description=description,
            species=species,
            hp=hp,
            dodge=dodge,
            prot=prot,
            spd=spd,
            max_hp=hp,
            type="enemy",
        )
        encounter.add_entity(EntityEnum.ENEMY, enemy)
        level.current_room = room_name
        return f'Added {name} to {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'

    @AILibFunction(
        name="add_treasure",
        description="Add a treasure to a room or corridor.",
        required=[
            "room_name",
            "cell_index",
            "name",
            "description",
            "loot",
            "trapped_chance",
            "dmg",
            "modifier_type",
            "modifier_chance",
            "modifier_turns",
            "modifier_amount",
        ],
    )
    @LibParam(room_name="The room (or corridor) name")
    @LibParam(
        cell_index="The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor."
    )
    @LibParam(name="The name of the treasure")
    @LibParam(description="The physical characteristics of the treasure")
    @LibParam(loot="The description of the loot in the treasure")
    @LibParam(
        trapped_chance="The chance that this treasure's trap gets triggered (between 0.0 and 1.0)"
    )
    @LibParam(
        dmg=f"The damage this treasure deals if the internal trap is triggered. Must be between {config.min_base_dmg} and {config.max_base_dmg}."
    )
    @LibParam(
        modifier_type=f'The type of modifier this treasure applies when triggered. Set to "no-modifier" if no modifier should be applied or if trapped_chance is 0, else set it to one of {", ".join([x.value for x in ModifierType])}.'
    )
    @LibParam(
        modifier_chance="The chance that the modifier is applied to a target (between 0.0 and 1.0)"
    )
    @LibParam(modifier_turns="The number of turns the modifier is active for")
    @LibParam(
        modifier_amount=f'The amount the modifier applies. A modifier exists only when trapped_chance is greater than 0. If the modifier is "bleed" or "heal", the value must be between {config.min_base_dmg} and {config.max_base_dmg}, otherwise it must be between 0.0 and 1.0.'
    )
    def add_treasure(
        self,
        level: Level,
        room_name: str,
        name: str,
        description: str,
        loot: str,
        trapped_chance: float,
        dmg: float,
        modifier_type: str,
        modifier_chance: float,
        modifier_turns: float,
        modifier_amount: float,
        cell_index: int,
    ) -> str:
        assert room_name != "", "Parameter room_name should be provided."
        assert name != "", "Treasure name should be provided."
        assert description != "", "Treasure description should be provided."
        assert loot != "", "Treasure loot should be provided."
        assert trapped_chance is not None, "Treasure trapped chance should be provided."
        assert dmg is not None, "Treasure damage should be provided."
        assert modifier_type != "", "Treasure modifier type should be provided."
        assert (
            modifier_chance is not None
        ), "Treasure modifier chance should be provided."
        assert modifier_turns is not None, "Treasure modifier turns should be provided."
        assert (
            modifier_amount is not None
        ), "Treasure modifier amount should be provided."
        encounter = get_encounter(level, room_name, cell_index)
        assert name not in [
            treasure.name for treasure in encounter.entities[EntityEnum.TREASURE.value]
        ], f'Could not add treasure: {name} already exists in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
        assert (
            0
            <= len(encounter.entities.get(EntityEnum.TREASURE.value, []))
            < config.max_treasures_per_encounter
        ), f'Could not add treasure: there is already {config.max_treasures_per_encounter} treasure(s) in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}, which is the maximum number allowed.'
        assert (
            0.0 <= trapped_chance <= 1.0
        ), f"trapped_chance must be a value between 0.0 and 1.0; you passed {trapped_chance}."
        treasure = Treasure(
            name=name,
            description=description,
            loot=loot,
            trapped_chance=trapped_chance,
            dmg=dmg,
            type="treasure",
        )
        if modifier_type != "no-modifier":
            assert modifier_type in [
                x.value for x in ModifierType
            ], f"Could not add treasure: {modifier_type} is not a valid modifier type."
            assert (
                0.0 <= modifier_chance <= 1.0
            ), f"modifier_chance must be a value between 0.0 and 1.0; you passed {modifier_chance}."
            assert (
                modifier_turns >= 0
            ), f"modifier_turns must be a positive value; you passed {modifier_turns}."
            if modifier_type in [ModifierType.BLEED.value, ModifierType.HEAL.value]:
                assert (
                    config.min_base_dmg <= modifier_amount <= config.max_base_dmg
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between {config.min_base_dmg} and {config.max_base_dmg}."
            elif modifier_type == ModifierType.SCARE.value:
                assert (
                    0.0 <= modifier_amount <= 1.0
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between 0.0 and 1.0."
            treasure.modifier = Modifier(
                type=modifier_type,
                chance=modifier_chance,
                turns=modifier_turns,
                amount=modifier_amount,
            )
        encounter.add_entity(EntityEnum.TREASURE, treasure)
        level.current_room = room_name
        return f'Added {name} to {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'

    @AILibFunction(
        name="add_trap",
        description="Add a trap to a corridor. Traps can be added only to corridors, not to rooms.",
        required=[
            "corridor_name",
            "cell_index",
            "name",
            "description",
            "effect",
            "chance",
            "dmg",
            "modifier_type",
            "modifier_chance",
            "modifier_turns",
            "modifier_amount",
        ],
    )
    @LibParam(corridor_name="The corridor name")
    @LibParam(
        cell_index="The corridor cell. Set to a value between 1 and the length of the corridor."
    )
    @LibParam(name="The name of the trap")
    @LibParam(description="The physical characteristics of the trap")
    @LibParam(effect="The effect of the trap")
    @LibParam(chance="The chance this trap gets triggered (between 0.0 and 1.0)")
    @LibParam(
        dmg=f"The damage this trap deals when triggered. Must be between {config.min_base_dmg} and {config.max_base_dmg}."
    )
    @LibParam(
        modifier_type=f'The type of modifier this trap applies when triggered. Set to "no-modifier" if no modifier should be applied, else set it to one of {", ".join([x.value for x in ModifierType])}.'
    )
    @LibParam(
        modifier_chance="The chance that the modifier is applied to a target (between 0.0 and 1.0)"
    )
    @LibParam(modifier_turns="The number of turns the modifier is active for")
    @LibParam(
        modifier_amount=f'The amount the modifier applies. If the modifier is "bleed" or "heal", the value must be between {config.min_base_dmg} and {config.max_base_dmg}, otherwise it must be between 0.0 and 1.0.'
    )
    def add_trap(
        self,
        level: Level,
        corridor_name: str,
        name: str,
        description: str,
        effect: str,
        chance: float,
        dmg: float,
        modifier_type: str,
        modifier_chance: float,
        modifier_turns: float,
        modifier_amount: float,
        cell_index: int,
    ) -> str:
        assert corridor_name != "", "Parameter corridor_name should be provided."
        assert name != "", "Trap name should be provided."
        assert description != "", "Trap description should be provided."
        assert effect != "", "Trap effect should be provided."
        assert chance is not None, "Trap chance should be provided."
        assert dmg is not None, "Trap damage should be provided."
        assert modifier_type != "", "Trap modifier type should be provided."
        assert modifier_chance is not None, "Trap modifier chance should be provided."
        assert modifier_turns is not None, "Trap modifier turns should be provided."
        assert modifier_amount is not None, "Trap modifier amount should be provided."
        assert (
            corridor_name in level.corridors.keys()
        ), f"Traps can only be added only to corridors, but {corridor_name} seems to be a room."
        corridor = level.corridors[corridor_name]
        assert corridor is not None, f"Corridor {corridor_name} does not exist."
        assert (
            0 < cell_index <= corridor.length
        ), f"{corridor_name} is a corridor, but cell_index={cell_index} is invalid, it should be a value between 1 and {corridor.length} (inclusive)."
        encounter = corridor.encounters[cell_index - 1]
        assert name not in [
            trap.name for trap in encounter.entities[EntityEnum.TRAP.value]
        ], f"Could not add trap: {name} already exists in {corridor_name} in cell {cell_index}."
        assert (
            0
            <= len(encounter.entities.get(EntityEnum.TRAP.value, []))
            < config.max_traps_per_encounter
        ), f"Could not add trap: there is already {config.max_traps_per_encounter} trap(s) in {corridor_name} in cell {cell_index}."
        assert (
            0.0 <= chance <= 1.0
        ), f"chance must be a value between 0.0 and 1.0; you passed {chance}."
        trap = Trap(
            name=name,
            description=description,
            effect=effect,
            chance=chance,
            dmg=dmg,
            type="trap",
        )
        if modifier_type != "no-modifier":
            assert modifier_type in [
                x.value for x in ModifierType
            ], f"Could not add trap: {modifier_type} is not a valid modifier type."
            assert (
                0.0 <= modifier_chance <= 1.0
            ), f"modifier_chance must be a value between 0.0 and 1.0; you passed {modifier_chance}."
            assert (
                modifier_turns >= 0
            ), f"modifier_turns must be a positive value; you passed {modifier_turns}."
            if modifier_type in [ModifierType.BLEED.value, ModifierType.HEAL.value]:
                assert (
                    config.min_base_dmg <= modifier_amount <= config.max_base_dmg
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between {config.min_base_dmg} and {config.max_base_dmg}."
            elif modifier_type == ModifierType.SCARE.value:
                assert (
                    0.0 <= modifier_amount <= 1.0
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between 0.0 and 1.0."
            trap.modifier = Modifier(
                type=modifier_type,
                chance=modifier_chance,
                turns=modifier_turns,
                amount=modifier_amount,
            )
        encounter.add_entity(EntityEnum.TRAP, trap)
        level.current_room = corridor_name
        return f"Added {name} in {corridor_name} in cell {cell_index}."

    @AILibFunction(
        name="update_enemy_properties",
        description="Update properties of an enemy in a room or corridor. Pass the current properties if they're not being updated. To move an enemy to a different room or corridor, remove it first and then add it again.",
        required=[
            "room_name",
            "cell_index",
            "reference_name",
            "name",
            "description",
            "species",
            "hp",
            "dodge",
            "prot",
            "spd",
        ],
    )
    @LibParam(room_name="The room (or corridor) name")
    @LibParam(
        cell_index="The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor."
    )
    @LibParam(reference_name="The reference name of the enemy to update")
    @LibParam(name="The unique updated name of the enemy")
    @LibParam(description="The unique updated physical characteristics of the enemy")
    @LibParam(species="The updated species of the enemy")
    @LibParamSpec(
        name="hp",
        description=f"The health points of the enemy, the value must be between {config.min_hp} and {config.max_hp}.",
    )
    @LibParamSpec(
        name="dodge",
        description=f"The dodge points of the enemy, the value must be between {config.min_dodge} and {config.max_dodge}.",
    )
    @LibParamSpec(
        name="prot",
        description=f"The protection points of the enemy, the value must be between {config.min_prot} and {config.max_prot}.",
    )
    @LibParamSpec(
        name="spd",
        description=f"The speed points of the enemy, the value must be between {config.min_spd} and {config.max_spd}.",
    )
    def update_enemy_properties(
        self,
        level: Level,
        room_name: str,
        reference_name: str,
        name: str,
        description: str,
        species: str,
        hp: float,
        dodge: float,
        prot: float,
        spd: float,
        cell_index: int,
    ) -> str:
        assert room_name != "", "Parameter room_name should be provided."
        assert reference_name != "", "Enemy reference name should be provided."
        assert name != "", "Enemy name should be provided."
        assert description != "", "Enemy description should be provided."
        assert species != "", "Enemy species should be provided."
        assert (
            config.min_hp <= hp <= config.max_hp
        ), f"Invalid hp value: {hp}; should be between {config.min_hp} and {config.max_hp}."
        assert (
            config.min_dodge <= dodge <= config.max_dodge
        ), f"Invalid dodge value: {dodge}; should be between {config.min_dodge} and {config.max_dodge}."
        assert (
            config.min_prot <= prot <= config.max_prot
        ), f"Invalid prot value: {prot}; should be between {config.min_prot} and {config.max_prot}."
        assert (
            config.min_spd <= spd <= config.max_spd
        ), f"Invalid spd value: {spd}; should be between {config.min_spd} and {config.max_spd}."
        encounter = get_encounter(level, room_name, cell_index)
        ref_enemy = encounter.get_entity_by_name(EntityEnum.ENEMY, reference_name)
        assert (
            ref_enemy is not None
        ), f'{reference_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
        assert (reference_name == name) or (
            name not in [enemy.name for enemy in encounter.enemies]
        ), f'{name} already exists in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
        updated_enemy = Enemy(
            name=name,
            description=description,
            species=species,
            hp=hp,
            dodge=dodge,
            prot=prot,
            spd=spd,
            max_hp=hp,
            type="enemy",
        )
        updated_enemy.attacks = ref_enemy.attacks
        encounter.replace_entity(reference_name, EntityEnum.ENEMY, updated_enemy)
        level.current_room = room_name
        return f"Updated {reference_name} properties in {room_name}."

    @AILibFunction(
        name="update_treasure_properties",
        description="Update properties of a treasure in a room or corridor. Pass the current properties if they're not being updated. To move a treasure to a different room or corridor, remove it first and then add it again.",
        required=[
            "room_name",
            "cell_index",
            "reference_name",
            "name",
            "description",
            "loot",
            "trapped_chance",
            "dmg",
            "modifier_type",
            "modifier_chance",
            "modifier_turns",
            "modifier_amount",
        ],
    )
    @LibParam(room_name="The room (or corridor) name")
    @LibParam(
        cell_index="The corridor cell. Set to None when targeting a room, otherwise set to a value between 1 and the length of the corridor."
    )
    @LibParam(reference_name="The reference name of the treasure to update")
    @LibParam(name="The updated name of the treasure")
    @LibParam(description="The updated physical characteristics of the treasure")
    @LibParam(loot="The updated loot description of the treasure")
    @LibParam(
        trapped_chance="The updated chance that this treasure's trap gets triggered (between 0.0 and 1.0)"
    )
    @LibParam(
        dmg=f"The updated damage this treasure deals if the internal trap is triggered. Must be between {config.min_base_dmg} and {config.max_base_dmg}."
    )
    @LibParam(
        modifier_type=f'The updated type of modifier this treasure applies when triggered. Set to "no-modifier" to remove the modifier or if trapped_chance is 0, else set it to one of {", ".join([x.value for x in ModifierType])}.'
    )
    @LibParam(
        modifier_chance="The updated chance that the modifier is applied to a target (between 0.0 and 1.0)"
    )
    @LibParam(modifier_turns="The updated number of turns the modifier is active for")
    @LibParam(
        modifier_amount=f'The updated amount the modifier applies. If the modifier is "bleed" or "heal", the value must be between {config.min_base_dmg} and {config.max_base_dmg}, otherwise it must be between 0.0 and 1.0.'
    )
    def update_treasure_properties(
        self,
        level: Level,
        room_name: str,
        reference_name: str,
        name: str,
        description: str,
        loot: str,
        trapped_chance: float,
        dmg: float,
        modifier_type: str,
        modifier_chance: float,
        modifier_turns: float,
        modifier_amount: float,
        cell_index: int,
    ) -> str:
        assert room_name != "", "Parameter room_name should be provided."
        assert reference_name != "", "Treasure reference name should be provided."
        assert name != "", "Treasure name should be provided."
        assert description != "", "Treasure description should be provided."
        assert loot != "", "Treasure loot should be provided."
        assert trapped_chance is not None, "Treasure trapped chance should be provided."
        assert dmg is not None, "Treasure damage should be provided."
        assert modifier_type != "", "Treasure modifier type should be provided."
        assert (
            modifier_chance is not None
        ), "Treasure modifier chance should be provided."
        assert modifier_turns is not None, "Treasure modifier turns should be provided."
        assert (
            modifier_amount is not None
        ), "Treasure modifier amount should be provided."
        encounter = get_encounter(level, room_name, cell_index)
        assert reference_name in [
            treasure.name for treasure in encounter.entities[EntityEnum.TREASURE.value]
        ], f'{reference_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
        assert (reference_name == name) or (
            name
            not in [
                treasure.name
                for treasure in encounter.entities[EntityEnum.TREASURE.value]
            ]
        ), f'{name} already exists in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
        assert (
            0.0 <= trapped_chance <= 1.0
        ), f"trapped_chance must be a value between 0.0 and 1.0; you passed {trapped_chance}."
        updated_treasure = Treasure(
            name=name,
            description=description,
            loot=loot,
            trapped_chance=trapped_chance,
            dmg=dmg,
            type="treasure",
        )
        if modifier_type != "no-modifier":
            assert modifier_type in [
                x.value for x in ModifierType
            ], f"Could not update treasure: {modifier_type} is not a valid modifier type."
            assert (
                0.0 <= modifier_chance <= 1.0
            ), f"modifier_chance must be a value between 0.0 and 1.0; you passed {modifier_chance}."
            assert (
                modifier_turns >= 0
            ), f"modifier_turns must be a positive value; you passed {modifier_turns}."
            if modifier_type in [ModifierType.BLEED.value, ModifierType.HEAL.value]:
                assert (
                    config.min_base_dmg <= modifier_amount <= config.max_base_dmg
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between {config.min_base_dmg} and {config.max_base_dmg}."
            elif modifier_type == ModifierType.SCARE.value:
                assert (
                    0.0 <= modifier_amount <= 1.0
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between 0.0 and 1.0."
            updated_treasure.modifier = Modifier(
                type=modifier_type,
                chance=modifier_chance,
                turns=modifier_turns,
                amount=modifier_amount,
            )
        encounter.replace_entity(reference_name, EntityEnum.TREASURE, updated_treasure)
        level.current_room = room_name
        return f"Updated {reference_name} properties in {room_name}."

    @AILibFunction(
        name="update_trap_properties",
        description="Update properties of a trap in a corridor. Pass the current properties if they're not being updated. To move a trap to a different corridor or corridor cell, remove it first and then add it again.",
        required=[
            "corridor_name",
            "cell_index",
            "reference_name",
            "name",
            "description",
            "effect",
            "chance",
            "dmg",
            "modifier_type",
            "modifier_chance",
            "modifier_turns",
            "modifier_amount",
        ],
    )
    @LibParam(corridor_name="The corridor name")
    @LibParam(
        cell_index="The corridor cell. Set it to a value between 1 and the length of the corridor."
    )
    @LibParam(reference_name="The reference name of the trap to update")
    @LibParam(name="The updated name of the traps")
    @LibParam(description="The updated physical characteristics of the trap")
    @LibParam(effect="The updated effects descriptions of the trap")
    @LibParam(chance="The chance this trap gets triggered (between 0.0 and 1.0)")
    @LibParam(
        dmg=f"The damage this trap deals when triggered. Must be between {config.min_base_dmg} and {config.max_base_dmg}."
    )
    @LibParam(
        modifier_type=f'The updated type of modifier this trap applies when triggered. Set to "no-modifier" to remove the modifier, else set it to one of {", ".join([x.value for x in ModifierType])}.'
    )
    @LibParam(
        modifier_chance="The chance that the modifier is applied to a target (between 0.0 and 1.0)"
    )
    @LibParam(modifier_turns="The number of turns the modifier is active for")
    @LibParam(
        modifier_amount=f'The amount the modifier applies. If the modifier is "bleed" or "heal", the value must be between {config.min_base_dmg} and {config.max_base_dmg}, otherwise it must be between 0.0 and 1.0.'
    )
    def update_trap_properties(
        self,
        level: Level,
        corridor_name: str,
        reference_name: str,
        name: str,
        description: str,
        effect: str,
        chance: float,
        dmg: float,
        modifier_type: str,
        modifier_chance: float,
        modifier_turns: float,
        modifier_amount: float,
        cell_index: int = None,
    ) -> str:
        assert corridor_name != "", "Parameter corridor_name should be provided."
        assert reference_name != "", "Trap reference name should be provided."
        assert name != "", "Trap name should be provided."
        assert description != "", "Trap description should be provided."
        assert effect != "", "Trap effect should be provided."
        assert chance is not None, "Trap chance should be provided."
        assert dmg is not None, "Trap danage should be provided."
        assert modifier_type != "", "Trap modifier type should be provided."
        assert modifier_chance is not None, "Trap modifier chance should be provided."
        assert modifier_turns is not None, "Trap modifier turns should be provided."
        assert modifier_amount is not None, "Trap modifier amount should be provided."
        corridor = level.corridors.get(corridor_name, None)
        assert corridor is not None, f"Corridor {corridor_name} does not exist."
        assert (
            0 < cell_index <= corridor.length
        ), f"{corridor_name} is a corridor, but cell_index={cell_index} is invalid, it should be a value between 1 and {corridor.length} (inclusive)."
        encounter = corridor.encounters[cell_index - 1]
        assert reference_name in [
            trap.name for trap in encounter.entities[EntityEnum.TRAP.value]
        ], f"{reference_name} does not exist in {corridor_name} in cell {cell_index}."
        assert (reference_name == name) or (
            name
            not in [trap.name for trap in encounter.entities[EntityEnum.TRAP.value]]
        ), f"{name} already exists in {corridor_name} in cell {cell_index}."
        assert (
            0.0 <= chance <= 1.0
        ), f"chance must be a value between 0.0 and 1.0; you passed {chance}."
        updated_trap = Trap(
            name=name,
            description=description,
            effect=effect,
            chance=chance,
            dmg=dmg,
            type="trap",
        )
        if modifier_type != "no-modifier":
            assert modifier_type in [
                x.value for x in ModifierType
            ], f"Could not update trap: {modifier_type} is not a valid modifier type."
            assert (
                0.0 <= modifier_chance <= 1.0
            ), f"modifier_chance must be a value between 0.0 and 1.0; you passed {modifier_chance}."
            assert (
                modifier_turns >= 0
            ), f"modifier_turns must be a positive value; you passed {modifier_turns}."
            if modifier_type in [ModifierType.BLEED.value, ModifierType.HEAL.value]:
                assert (
                    config.min_base_dmg <= modifier_amount <= config.max_base_dmg
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between {config.min_base_dmg} and {config.max_base_dmg}."
            elif modifier_type == ModifierType.SCARE.value:
                assert (
                    0.0 <= modifier_amount <= 1.0
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between 0.0 and 1.0."
            updated_trap.modifier = Modifier(
                type=modifier_type,
                chance=modifier_chance,
                turns=modifier_turns,
                amount=modifier_amount,
            )
        encounter.replace_entity(reference_name, EntityEnum.TRAP, updated_trap)
        level.current_room = corridor_name
        return f"Updated {reference_name} properties in {corridor_name}."

    @AILibFunction(
        name="remove_entity",
        description="Remove an entity (an enemy, a trap, or a treasure) from a room or corridor",
        required=["room_name", "cell_index", "entity_name", "entity_type"],
    )
    @LibParam(room_name="The room (or corridor) name")
    @LibParam(
        cell_index="The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor."
    )
    @LibParam(entity_name="The name of the entity")
    @LibParam(
        entity_type='The type of the entity; must be of "enemy", "trap", or "treasure"'
    )
    def remove_entity(
        self,
        level: Level,
        room_name: str,
        entity_name: str,
        entity_type: str,
        cell_index: int,
    ) -> str:
        assert room_name != "", "Parameter room_name should be provided."
        assert entity_name != "", "Entity name should be provided."
        assert entity_type != "", "Entity type should be provided."
        entity_enum = get_enum_by_value(EntityEnum, entity_type)
        assert entity_enum is not None, f"Invalid entity type: {entity_type}."
        encounter = get_encounter(level, room_name, cell_index)
        assert entity_name in [
            entity.name for entity in encounter.entities[entity_enum.value]
        ], f'{entity_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
        encounter.remove_entity_by_name(entity_enum, entity_name)
        level.current_room = room_name
        return f"Removed {entity_name} from {room_name}."

    @AILibFunction(
        name="add_attack",
        description="Add an attack to an enemy.",
        required=[
            "room_name",
            "cell_index",
            "enemy_name",
            "name",
            "description",
            "starting_positions",
            "target_positions",
            "base_dmg",
            "modifier_type",
            "modifier_chance",
            "modifier_turns",
            "modifier_amount",
        ],
    )
    @LibParam(room_name="The room (or corridor) name")
    @LibParam(
        cell_index="The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor."
    )
    @LibParam(enemy_name="The unique name of the enemy.")
    @LibParam(name="The unique name of the attack.")
    @LibParam(description="The description of the attack.")
    @LibParam(attack_type='The attack type: must be one of "damage" or "heal".')
    @LibParam(
        starting_positions='A string of 4 characters describing the positions from which the attack can be executed. Use "X" where the attack can be executed from, and "O" otherwise.'
    )
    @LibParam(
        target_positions='A string of 4 characters describing the positions that the attack strikes to. Use "X" where the attack strikes to, and "O" otherwise.'
    )
    @LibParam(
        base_dmg=f"The base damage of the attack. Must be between {config.min_base_dmg} and {config.max_base_dmg}."
    )
    @LibParam(accuracy="The attack accuracy (a percentage between 0.0 and 1.0).")
    @LibParam(
        modifier_type=f'The type of modifier this attack applies when triggered. Set to "no-modifier" if no modifier should be applied, else set it to one of {", ".join([x.value for x in ModifierType])}.'
    )
    @LibParam(
        modifier_chance="The chance that the modifier is applied to a target (between 0.0 and 1.0)"
    )
    @LibParam(modifier_turns="The number of turns the modifier is active for")
    @LibParam(
        modifier_amount=f'The amount the modifier applies. If the modifier is "bleed" or "heal", the value must be between {config.min_base_dmg} and {config.max_base_dmg}, otherwise it must be between 0.0 and 1.0.'
    )
    def add_attack(
        self,
        level: Level,
        room_name: str,
        cell_index: int,
        enemy_name: str,
        name: str,
        description: str,
        attack_type: str,
        starting_positions: str,
        target_positions: str,
        base_dmg: float,
        accuracy: float,
        modifier_type: str,
        modifier_chance: float,
        modifier_turns: float,
        modifier_amount: float,
    ) -> str:
        assert room_name != "", f"Parameter room_name should be provided."
        assert name != "", f"Attack name should be specified."
        assert description != "", f"Attack description should be specified."
        assert enemy_name != "", f"Enemy name should be specified."
        assert modifier_type != "", "Attack modifier type should be provided."
        assert modifier_chance is not None, "Attack modifier chance should be provided."
        assert modifier_turns is not None, "Attack modifier turns should be provided."
        assert modifier_amount is not None, "Attack modifier amount should be provided."
        type_enum = get_enum_by_value(ActionType, attack_type)
        assert (
            type_enum is not None
        ), f'Attack type "{attack_type}" is not a valid type: it must be one of {", ".join([t.value for t in ActionType])}.'
        if type_enum == ActionType.DAMAGE:
            assert (
                config.min_base_dmg <= base_dmg <= config.max_base_dmg
            ), f"Invalid base_dmg value: {base_dmg}; should be between {config.min_base_dmg} and {config.max_base_dmg}."
        else:  # type is HEAL
            assert (
                -config.max_base_dmg <= base_dmg <= -config.min_base_dmg
            ), f"Invalid base_dmg value: {base_dmg}; should be between {-config.max_base_dmg} and {-config.min_base_dmg}."
        assert 0.0 <= accuracy <= 1.0, f"Invalid accuracy: must be between 0.0 and 1.0"
        assert (
            len(starting_positions) == 4
        ), f"Invalid starting_positions value: {starting_positions}. Must be 4 characters long."
        assert (
            len(target_positions) == 4
        ), f"Invalid target_positions value: {target_positions}. Must be 4 characters long."
        assert set(starting_positions).issubset(
            {"X", "O"}
        ), f'Invalid starting_positions value: {starting_positions}. Must contain only "X" and "O" characters.'
        assert set(target_positions).issubset(
            {"X", "O"}
        ), f'Invalid target_positions value: {target_positions}. Must contain only "X" and "O" characters.'
        encounter = get_encounter(level, room_name, cell_index)
        assert enemy_name in [
            entity.name for entity in encounter.entities[EntityEnum.ENEMY.value]
        ], f'{enemy_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
        enemy: Enemy = encounter.entities[EntityEnum.ENEMY.value][
            [
                entity.name for entity in encounter.entities[EntityEnum.ENEMY.value]
            ].index(enemy_name)
        ]
        assert (
            len(enemy.attacks) < config.max_num_attacks
        ), f"Enemy {enemy.name} has {config.max_num_attacks}, which is the maximum amount allowed."
        attack = Attack(
            name=name,
            description=description,
            type=type_enum,
            starting_positions=starting_positions,
            target_positions=target_positions,
            base_dmg=base_dmg,
            accuracy=accuracy,
        )
        if modifier_type != "no-modifier":
            assert modifier_type in [
                x.value for x in ModifierType
            ], f"Could not add attack: {modifier_type} is not a valid modifier type."
            assert (
                0.0 <= modifier_chance <= 1.0
            ), f"modifier_chance must be a value between 0.0 and 1.0; you passed {modifier_chance}."
            assert (
                modifier_turns >= 0
            ), f"modifier_turns must be a positive value; you passed {modifier_turns}."
            if modifier_type in [ModifierType.BLEED.value, ModifierType.HEAL.value]:
                assert (
                    config.min_base_dmg <= modifier_amount <= config.max_base_dmg
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between {config.min_base_dmg} and {config.max_base_dmg}."
            elif modifier_type == ModifierType.SCARE.value:
                assert (
                    0.0 <= modifier_amount <= 1.0
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between 0.0 and 1.0."
            attack.modifier = Modifier(
                type=modifier_type,
                chance=modifier_chance,
                turns=modifier_turns,
                amount=modifier_amount,
            )
        enemy.attacks.append(attack)
        level.current_room = room_name
        return f"Added {name} to {enemy_name}."

    @AILibFunction(
        name="update_attack",
        description="Update the properties of an attack of an enemy. Pass the current properties if they're not being updated.",
        required=[
            "room_name",
            "cell_index",
            "enemy_name",
            "reference_name",
            "name",
            "description",
            "starting_positions",
            "target_positions",
            "base_dmg",
            "modifier_type",
            "modifier_chance",
            "modifier_turns",
            "modifier_amount",
        ],
    )
    @LibParam(room_name="The room (or corridor) name")
    @LibParam(
        cell_index="The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor."
    )
    @LibParam(enemy_name="The unique name of the enemy.")
    @LibParam(reference_name="The reference name of the attack to update")
    @LibParam(name="The updated unique name of the attack.")
    @LibParam(description="The updated description of the attack.")
    @LibParam(attack_type='The updated attack type: must be one of "damage" or "heal".')
    @LibParam(
        starting_positions='The updated string of 4 characters describing the positions from which the attack can be executed. Use "X" where the attack can be executed from, and "O" otherwise.'
    )
    @LibParam(
        target_positions='The updated string of 4 characters describing the positions that the attack strikes to. Use "X" where the attack strikes to, and "O" otherwise.'
    )
    @LibParam(
        base_dmg=f"The updated base damage of the attack. Must be between {config.min_base_dmg} and {config.max_base_dmg}."
    )
    @LibParam(
        accuracy="The updated attack accuracy (a percentage between 0.0 and 1.0)."
    )
    @LibParam(
        modifier_type=f'The updated type of modifier this attack applies when triggered. Set to "no-modifier" if no modifier should be applied, else set it to one of {", ".join([x.value for x in ModifierType])}.'
    )
    @LibParam(
        modifier_chance="The updated chance that the modifier is applied to a target (between 0.0 and 1.0)"
    )
    @LibParam(modifier_turns="The updated number of turns the modifier is active for")
    @LibParam(
        modifier_amount=f'The updated amount the modifier applies. If the modifier is "bleed" or "heal", the value must be between {config.min_base_dmg} and {config.max_base_dmg}, otherwise it must be between 0.0 and 1.0.'
    )
    def update_attack(
        self,
        level: Level,
        room_name: str,
        cell_index: int,
        enemy_name: str,
        reference_name: str,
        name: str,
        description: str,
        attack_type: str,
        starting_positions: str,
        target_positions: str,
        base_dmg: float,
        accuracy: float,
        modifier_type: str,
        modifier_chance: float,
        modifier_turns: float,
        modifier_amount: float,
    ) -> str:
        assert room_name != "", f"Parameter room_name should be provided."
        assert reference_name != "", f"Attack reference name should be specified."
        assert name != "", f"Attack name should be specified."
        assert description != "", f"Attack description should be specified."
        assert enemy_name != "", f"Enemy name should be specified."
        assert modifier_type != "", "Attack modifier type should be provided."
        assert modifier_chance is not None, "Attack modifier chance should be provided."
        assert modifier_turns is not None, "Attack modifier turns should be provided."
        assert modifier_amount is not None, "Attack modifier amount should be provided."
        type_enum = get_enum_by_value(ActionType, attack_type)
        assert (
            type_enum is not None
        ), f'Attack type "{attack_type}" is not a valid type: it must be one of {", ".join([t.value for t in ActionType])}.'
        if type_enum == ActionType.DAMAGE:
            assert (
                config.min_base_dmg <= base_dmg <= config.max_base_dmg
            ), f"Invalid base_dmg value: {base_dmg}; should be between {config.min_base_dmg} and {config.max_base_dmg}."
        else:  # type is HEAL
            assert (
                -config.max_base_dmg <= base_dmg <= -config.min_base_dmg
            ), f"Invalid base_dmg value: {base_dmg}; should be between {-config.max_base_dmg} and {-config.min_base_dmg}."
        assert (
            len(starting_positions) == 4
        ), f"Invalid starting_positions value: {starting_positions}. Must be 4 characters long."
        assert (
            len(target_positions) == 4
        ), f"Invalid target_positions value: {target_positions}. Must be 4 characters long."
        assert set(starting_positions).issubset(
            {"X", "O"}
        ), f'Invalid starting_positions value: {starting_positions}. Must contain only "X" and "O" characters.'
        assert set(starting_positions).issubset(
            {"X", "O"}
        ), f'Invalid target_positions value: {target_positions}. Must contain only "X" and "O" characters.'
        encounter = get_encounter(level, room_name, cell_index)
        assert enemy_name in [
            entity.name for entity in encounter.entities[EntityEnum.ENEMY.value]
        ], f'{enemy_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
        enemy: Enemy = encounter.entities[EntityEnum.ENEMY.value][
            [
                entity.name for entity in encounter.entities[EntityEnum.ENEMY.value]
            ].index(enemy_name)
        ]
        assert reference_name in [
            attack.name for attack in enemy.attacks
        ], f"{reference_name} is not an attack for {enemy_name}."
        idx = [attack.name for attack in enemy.attacks].index(reference_name)
        attack = Attack(
            name=name,
            description=description,
            type=type_enum,
            starting_positions=starting_positions,
            target_positions=target_positions,
            base_dmg=base_dmg,
            accuracy=accuracy,
        )
        if modifier_type != "no-modifier":
            assert modifier_type in [
                x.value for x in ModifierType
            ], f"Could not add attack: {modifier_type} is not a valid modifier type."
            assert (
                0.0 <= modifier_chance <= 1.0
            ), f"modifier_chance must be a value between 0.0 and 1.0; you passed {modifier_chance}."
            assert (
                modifier_turns >= 0
            ), f"modifier_turns must be a positive value; you passed {modifier_turns}."
            if modifier_type in [ModifierType.BLEED.value, ModifierType.HEAL.value]:
                assert (
                    config.min_base_dmg <= modifier_amount <= config.max_base_dmg
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between {config.min_base_dmg} and {config.max_base_dmg}."
            elif modifier_type == ModifierType.SCARE.value:
                assert (
                    0.0 <= modifier_amount <= 1.0
                ), f"Invalid modifier_amount value: {modifier_amount}; should be between 0.0 and 1.0."
            attack.modifier = Modifier(
                type=modifier_type,
                chance=modifier_chance,
                turns=modifier_turns,
                amount=modifier_amount,
            )
        enemy.attacks[idx] = attack
        level.current_room = room_name
        return f"Updated {reference_name} of {enemy_name}."

    @AILibFunction(
        name="remove_attack",
        description="Remove an attack from an enemy.",
        required=["room_name", "cell_index", "enemy_name", "name"],
    )
    @LibParam(room_name="The room (or corridor) name")
    @LibParam(
        cell_index="The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor."
    )
    @LibParam(enemy_name="The unique name of the enemy.")
    @LibParam(name="The unique name of the attack.")
    def remove_attack(
        self, level: Level, room_name: str, cell_index: int, enemy_name: str, name: str
    ) -> str:
        assert room_name != "", f"Parameter room_name should be provided."
        assert name != "", f"Attack name should be specified."
        assert enemy_name != "", f"Enemy name should be specified."
        encounter = get_encounter(level, room_name, cell_index)
        enemy: Enemy = encounter.entities[EntityEnum.ENEMY.value][
            [
                entity.name for entity in encounter.entities[EntityEnum.ENEMY.value]
            ].index(enemy_name)
        ]
        assert name in [
            attack.name for attack in enemy.attacks
        ], f"{name} is not an attack for {enemy_name}."
        idx = [attack.name for attack in enemy.attacks].index(name)
        enemy.attacks.pop(idx)
        level.current_room = room_name
        return f"Removed {name} from {enemy_name}."

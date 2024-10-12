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
from dungeon_despair.domain.room import Room
from dungeon_despair.domain.utils import Direction, get_enum_by_value, opposite_direction, EntityEnum, is_corridor, \
	derive_rooms_from_corridor_name, make_corridor_name, get_encounter, get_new_coords, check_if_in_loop, \
	check_intersection_coords, get_rotation, get_rotated_direction


class DungeonCrawlerFunctions(GPTFunctionLibrary):
	def try_call_func(self,
	                  func_name: str,
	                  func_args: str,
	                  level: Level) -> str:
		if isinstance(func_args, str):
			func_args = json.loads(func_args)
		try:
			operation_result = self.call_by_dict({
				'name': func_name,
				'arguments': {
					'level': level,
					**func_args
				}
			})
			return operation_result
		except AssertionError as e:
			return f'Domain validation error: {e}'
	
	@AILibFunction(name='create_room', description='Create a room in the level.',
	               required=['name', 'description', 'room_from', 'direction'])
	@LibParam(name='The room name')
	@LibParam(description='The room physical characteristics')
	@LibParam(
		room_from='The room the new room connects from. If unspecified, set it to \"\" if there is no current room, otherwise set it to the current room.')
	@LibParam(
		direction='The direction the new room connects from. If unspecified, set it to \"\" if there is no current room, otherwise set it to one of the available directions (either \"north\", \"south\", \"east\", or \"west\").')
	def create_room(self, level: Level,
	                name: str,
	                description: str,
	                room_from: str,
	                direction: str) -> str:
		assert name not in level.rooms.keys(), f'Could not add {name} to the level: {name} already exists.'
		if level.current_room == '':
			assert room_from == '', f'Could not add {name} to the level: room_from must not be set if there is no current room.'
		if level.current_room != '':
			assert room_from != '', f'Could not add {name} to the level: room_from must be set if there exists a current room (current room is {level.current_room}).'
			assert direction != '', f'Could not add {name} to the level: direction must be set if there exists a current room (current room is {level.current_room}).'
		if room_from != '':
			assert not is_corridor(
				level.current_room), f'Could not add {name} to the level: Cannot add a room from a corridor, try adding the room from either {derive_rooms_from_corridor_name(level.current_room)[0]} or {derive_rooms_from_corridor_name(level.current_room)[1]}.'
			assert room_from in level.rooms.keys(), f'{room_from} is not a valid room name.'
			dir_enum = get_enum_by_value(Direction, direction)
			assert dir_enum is not None, f'Could not add {name} to the level: {direction} is not a valid direction.'
			assert level.connections[room_from][
				       dir_enum] == '', f'Could not add {name} to the level: {direction} of {room_from} there already exists a room ({level.connections[room_from][dir_enum]}).'
			# try add corridor to connecting room
			n = len(level.get_corridors_by_room(name)) // 2
			# can only add corridor if the connecting room has at most 3 corridors already
			assert n < 4, f'Could not add {name} to the level: {room_from} has too many connections.'
			from_coords = level.rooms[room_from].coords
			new_coords = get_new_coords(coords=from_coords, direction=dir_enum, n=config.corridor_min_length + 1)
			intersects, intersection_name = check_intersection_coords(coords=new_coords, level=level)
			if intersects:
				raise AssertionError(f'Could not add {name} to the level: {name} would clash in {intersection_name}.')
			corridor_coords = [get_new_coords(coords=from_coords, direction=dir_enum, n=x) for x in range(1, config.corridor_min_length + 1)]
			for corridor_coord in corridor_coords:
				intersects, intersection_name = check_intersection_coords(coords=corridor_coord, level=level)
				if intersects:
					raise AssertionError(f'Could not add {name} to the level: corridor between {room_from} and {name} would clash in {intersection_name}.')
			# add the new room to the level
			level.rooms[name] = Room(name=name, description=description, coords=new_coords)
			level.current_room = name
			corridor = Corridor(room_from=room_from, room_to=name, name=f'{room_from}-{name}',
			                    direction=dir_enum, coords=corridor_coords)
			level.corridors[corridor.name] = corridor
			level.connections[name] = {direction: '' for direction in Direction}
			level.connections[room_from][dir_enum] = name
			level.connections[name][opposite_direction[dir_enum]] = room_from
			return f'Added {name} to the level.'
		else:
			# add the new room to the level
			level.rooms[name] = Room(name=name, description=description)
			level.current_room = name
			level.connections[name] = {direction: '' for direction in Direction}
			return f'Added {name} to the level.'
	
	@AILibFunction(name='remove_room', description='Remove the room from the level', required=['name'])
	@LibParam(name='The room name')
	def remove_room(self, level: Level,
	                name: str) -> str:
		assert name in level.rooms.keys(), f'Could not remove {name}: {name} is not in the level.'
		# remove room
		del level.rooms[name]
		del level.connections[name]
		# remove connections to deleted room
		to_remove = level.get_corridors_by_room(name)
		for corridor in to_remove:
			del level.corridors[corridor.name]
			# remove connections in "to" rooms
			for direction in Direction:
				if corridor.room_to in level.rooms.keys() and level.connections[corridor.room_to][direction] == name:
					level.connections[corridor.room_to][direction] = ''
					break
		level.current_room = list(level.rooms.keys())[0] if len(level.rooms) > 0 else ''
		# TODO: Should remove "hanging" rooms as well
		return f'{name} has been removed from the dungeon.'
	
	@AILibFunction(name='update_room', description='Update the room',
	               required=['room_reference_name', 'name', 'description'])
	@LibParam(room_reference_name='The original room name')
	@LibParam(name='The room name')
	@LibParam(description='The room physical characteristics')
	def update_room(self, level: Level,
	                room_reference_name: str,
	                name: str,
	                description: str) -> str:
		assert room_reference_name in level.rooms.keys(), f'Could not update {room_reference_name}: {room_reference_name} is not in the level.'
		if name != room_reference_name:
			assert name not in level.rooms.keys(), f'Could not update {room_reference_name}: {name} already exists in the level.'
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
				corridor.name = f'{room.name}-{corridor.room_to}'
				corridor.sprite = [None for _ in range(corridor.length)] if room.description != description else corridor.sprite
				level.corridors[corridor.name] = corridor
			if corridor.room_to == room_reference_name:
				del level.corridors[corridor.name]
				corridor.room_to = room.name
				corridor.name = f'{corridor.room_from}-{room.name}'
				corridor.sprite = [None for _ in range(corridor.length)] if room.description != description else corridor.sprite
				level.corridors[corridor.name] = corridor
		room.description = description
		# add room back
		level.rooms[name] = room
		# update level geometry
		room_connections = level.connections[room_reference_name]
		del level.connections[room_reference_name]
		level.connections[name] = room_connections
		for direction, other_room_name in level.connections[name].items():
			if other_room_name != '':
				level.connections[other_room_name][opposite_direction[direction]] = name
		if level.current_room == room_reference_name:
			level.current_room = name
		return f'Updated {room_reference_name}.'

	
	@AILibFunction(name='add_corridor', description='Add a corridor',
	               required=['room_from_name', 'room_to_name', 'corridor_length'])
	@LibParam(room_from_name='The starting room name')
	@LibParam(room_to_name='The connecting room name')
	@LibParamSpec(name='corridor_length', description='The corridor length', minimum=config.corridor_min_length,
	              maximum=config.corridor_max_length)
	@LibParam(
		direction='The direction of the corridor from room_from_name to room_to_name. Must be one of "north", "south", "east", or "west".')
	def add_corridor(self, level: Level,
	                 room_from_name: str,
	                 room_to_name: str,
	                 corridor_length: int,
	                 direction: str) -> str:
		assert room_from_name in level.rooms.keys(), f'Room {room_from_name} is not in the level.'
		assert room_to_name in level.rooms.keys(), f'Room {room_to_name} is not in the level.'
		corridor = level.get_corridor(room_from_name, room_to_name, ordered=False)
		assert corridor is None, f'Could not add corridor: a corridor between {room_from_name} and {room_to_name} already exists.'
		assert config.corridor_min_length <= corridor_length <= config.corridor_max_length, f'Could not add corridor: corridor_length should be between {config.corridor_min_length} and {config.corridor_max_length}, not {corridor_length}'
		dir_enum = get_enum_by_value(Direction, direction)
		assert dir_enum is not None, f'Could not add a corridor: {direction} is not a valid direction.'
		assert level.connections[room_from_name][
			       dir_enum] == '', f'Could not add corridor: {direction} of {room_from_name} already has a corridor to {level.connections[room_from_name][dir_enum]}.'
		n = (len(level.get_corridors_by_room(room_from_name)) // 2,
		     len(level.get_corridors_by_room(room_to_name)) // 2)  # number of corridors for each room
		# only add corridor if each room has at most 3 corridors
		assert n[0] < 4, f'Could not add corridor: {room_from_name} has already 4 connections.'
		assert n[1] < 4, f'Could not add corridor: {room_to_name} has already 4 connections.'
		# Check if the rooms are reachable with the specified corridor
		from_coords = level.rooms[room_from_name].coords
		to_coords = level.rooms[room_to_name].coords
		hyp_to_coords = get_new_coords(coords=from_coords, direction=dir_enum, n=corridor_length + 1)
		assert to_coords == hyp_to_coords, f'Could not add corridor: cannot reach {room_to_name} from {room_from_name} with a corridor of length {corridor_length} along {direction}.'
		# Check if the corridor doesn't intersect other rooms/corridors
		corridor_coords = [get_new_coords(coords=from_coords, direction=dir_enum, n=x) for x in range(1, corridor_length + 1)]
		for corridor_coord in corridor_coords:
			intersects, intersection_name = check_intersection_coords(coords=corridor_coord, level=level)
			if intersects:
				raise AssertionError(
					f'Could not add corridor between {room_from_name} and {room_to_name} to the level: it would clash in {intersection_name}.')
		# Update level and add the corridor
		level.connections[room_from_name][dir_enum] = room_to_name
		level.connections[room_to_name][opposite_direction[dir_enum]] = room_from_name
		corridor = Corridor(room_from=room_from_name, room_to=room_to_name,
		                    name=make_corridor_name(room_from_name, room_to_name),
		                    length=corridor_length,
		                    encounters=[Encounter() for _ in range(corridor_length)],
		                    direction=dir_enum,
		                    coords=corridor_coords)
		level.corridors[corridor.name] = corridor
		level.current_room = f'{room_from_name}-{room_to_name}'
		return f'Added corridor between {room_from_name} and {room_to_name}.'
	
	
	@AILibFunction(name='remove_corridor', description='Remove a corridor', required=['room_from_name', 'room_to_name'])
	@LibParam(room_from_name='The starting room name')
	@LibParam(room_to_name='The connecting room name')
	def remove_corridor(self, level: Level,
	                    room_from_name: str,
	                    room_to_name: str) -> str:
		corridor = level.get_corridor(room_from_name, room_to_name, ordered=False)
		assert corridor is not None, f'Corridor between {room_from_name} and {room_to_name} does not exist.'
		# remove the corridor from the level
		del level.corridors[corridor.name]
		# remove connection between the two rooms
		for room_a, room_b in [(room_from_name, room_to_name), (room_to_name, room_from_name)]:
			for direction in Direction:
				if level.connections[room_a][direction] == room_b:
					level.connections[room_a][direction] = ''
					break
		# update the current room if necessary
		if level.current_room == corridor.name:
			level.current_room = corridor.room_from
		# TODO: Should remove "hanging" rooms as well
		return f'Removed corridor between {room_from_name} and {room_to_name}.'
	
	
	@AILibFunction(name='update_corridor', description='Update a corridor',
	               required=['room_from_name', 'room_to_name', 'corridor_length'])
	@LibParam(room_from_name='The starting room name')
	@LibParam(room_to_name='The connecting room name')
	@LibParamSpec(name='corridor_length', description='The corridor length', minimum=config.corridor_min_length,
	              maximum=config.corridor_max_length)
	@LibParam(
		direction='The direction of the corridor from room_from_name to room_to_name. Must be one of "north", "south", "east", or "west".')
	def update_corridor(self, level: Level,
	                    room_from_name: str,
	                    room_to_name: str,
	                    corridor_length: int,
	                    direction: str) -> str:
		assert config.corridor_min_length <= corridor_length <= config.corridor_max_length, f'Could not add corridor: corridor_length should be between {config.corridor_min_length} and {config.corridor_max_length}, not {corridor_length}'
		corridor = level.get_corridor(room_from_name, room_to_name, ordered=False)
		assert corridor is not None, f'Corridor between {room_from_name} and {room_to_name} does not exist.'
		dir_enum = get_enum_by_value(Direction, direction)
		assert dir_enum is not None, f'Could not update corridor between {room_from_name} and {room_to_name}: {direction} is not a valid direction.'
		# corridors cannot be changed if in a loop
		assert not check_if_in_loop(corridor=corridor,
		                            connections=level.connections), 'Could not update corridor: corridors in a closed loop cannot be altered.'
		# Make a copy of parts of the level that would change and that would be fixed
		changing_rooms, changing_corridors = level.get_level_subset(corridor=corridor, opposite_direction=False)
		fixed_rooms, fixed_corridors = level.get_level_subset(corridor=corridor, opposite_direction=True)
		changing_corridors.insert(0, corridor)  # first element since changes are cascaded
		changing_rooms = {x.name: copy.deepcopy(x) for x in changing_rooms}
		changing_corridors = {x.name: copy.deepcopy(x) for x in changing_corridors}
		fixed_rooms = {x.name: copy.deepcopy(x) for x in fixed_rooms}
		fixed_corridors = {x.name: copy.deepcopy(x) for x in fixed_corridors}
		# Apply rotations first
		if dir_enum != corridor.direction:
			rotated = []
			rotate_by = get_rotation(from_direction=corridor.direction, to_direction=dir_enum)
			for c in changing_corridors.values():
				if c.name not in rotated:
					c.direction = get_rotated_direction(direction=c.direction, rotate_by=rotate_by)
					# room_from may be in fixed_rooms
					if c.room_from in fixed_rooms.keys():
						from_coords = fixed_rooms[c.room_from].coords
					else:
						from_coords = changing_rooms[c.room_from].coords
					c.coords = [get_new_coords(coords=from_coords,
					                           direction=c.direction,
					                           n=x) for x in range(1, c.length + 1)]
					# update the coordinates of the room_to
					changing_rooms[c.room_to].coords = get_new_coords(coords=c.coords[-1],
					                                                  direction=c.direction,
					                                                  n=1)
					rotated.append(c.name)
		# Apply corridor length change
		if corridor_length != corridor.length:
			updated = []
			changing_corridors[corridor.name].length = corridor_length
			for c in changing_corridors.values():
				if c.name not in updated:
					if c.room_from in fixed_rooms.keys():
						from_coords = fixed_rooms[c.room_from].coords
					else:
						from_coords = changing_rooms[c.room_from].coords
					c.coords = [get_new_coords(coords=from_coords,
					                           direction=c.direction,
					                           n=x) for x in range(1, c.length + 1)]
					changing_rooms[c.room_to].coords = get_new_coords(coords=c.coords[-1],
					                                                  direction=c.direction,
					                                                  n=1)
					updated.append(c.name)
		# Check for intersections with the fixed part of the level
		for changing_room in changing_rooms.values():
			for fixed_room in fixed_rooms.values():
				if changing_room.coords == fixed_room.coords:
					raise AssertionError(f'Could not update corridor between {room_from_name} and {room_to_name}: updated corridor would results in {changing_room.name} intersect with {fixed_room.name}')
			for fixed_corridor in fixed_corridors.values():
				if changing_room.coords in fixed_corridor.coords:
					raise AssertionError(
						f'Could not update corridor between {room_from_name} and {room_to_name}: updated corridor would results in {changing_room.name} intersect with {fixed_corridor.name}')
		for changing_corridor in changing_corridors.values():
			for fixed_room in fixed_rooms.values():
				if fixed_room.coords in changing_corridor.coords:
					raise AssertionError(
						f'Could not update corridor between {room_from_name} and {room_to_name}: updated corridor would results in {changing_corridor.name} intersect with {fixed_room.name}')
			for fixed_corridor in fixed_corridors.values():
				if len(set(changing_corridor.coords).difference(fixed_corridor.coords)) > 0:
					raise AssertionError(
						f'Could not update corridor between {room_from_name} and {room_to_name}: updated corridor would results in {changing_corridor.name} intersect with {fixed_corridor.name}')
		# If everything is fine, update the level (and the connections)
		# remove old connection
		level.connections[corridor.room_from][corridor.direction] = ''
		level.connections[corridor.room_to][opposite_direction[corridor.direction]] = ''
		# update rooms
		for room_name in changing_rooms.keys():
			level.rooms[room_name] = changing_rooms[room_name]
		# update corridors
		for corridor_name in changing_corridors.keys():
			level.corridors[corridor_name] = changing_corridors[corridor_name]
		# update connections
		for changing_corridor in changing_corridors.values():
			level.connections[changing_corridor.room_from][changing_corridor.direction] = changing_corridor.room_to
			level.connections[changing_corridor.room_to][opposite_direction[changing_corridor.direction]] = changing_corridor.room_from
		# Get the updated corridor
		corridor = level.corridors[corridor.name]
		# Update encounters and sprites if the length of the corridor has changed
		if len(corridor.encounters) != corridor.length:
			if len(corridor.encounters) > corridor.length:
				# Drop extra encounters
				corridor.encounters = corridor.encounters[:corridor.length]
				# Drop extra sprites
				last_sprite = corridor.sprites[-1]  # Last sprite is kept
				corridor.sprites = corridor.sprites[0:corridor.length + 1] + [last_sprite]
			else:
				while len(corridor.encounters) < corridor.length:
					# Add new, empty encounters
					corridor.encounters.append(Encounter())
					# Add empty sprite
					corridor.sprites.insert(-2, None)
		level.current_room = corridor.name
		return f'Updated corridor between {room_from_name} and {room_to_name}.'
	
	
	@AILibFunction(name='add_enemy', description='Add an enemy to a room or corridor.',
	               required=['room_name', 'cell_index', 'name', 'description', 'species', 'hp', 'dodge', 'prot', 'spd'])
	@LibParam(room_name='The room (or corridor) name')
	@LibParamSpec(name='cell_index',
	              description='The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor.')
	@LibParamSpec(name='name', description='The unique name of the enemy')
	@LibParamSpec(name='description', description='The physical description of the enemy')
	@LibParamSpec(name='species', description='The species of the enemy')
	@LibParamSpec(name='hp',
	              description=f'The health points of the enemy, must be a value must be between {config.min_hp} and {config.max_hp}.')
	@LibParamSpec(name='dodge',
	              description=f'The dodge points of the enemy, must be a value must be between {config.min_dodge} and {config.max_dodge}.')
	@LibParamSpec(name='prot',
	              description=f'The protection points of the enemy, must be a value must be between {config.min_prot} and {config.max_prot}.')
	@LibParamSpec(name='spd',
	              description=f'The speed points of the enemy, must be a value must be between {config.min_spd} and {config.max_spd}.')
	def add_enemy(self, level: Level,
	              room_name: str,
	              name: str,
	              description: str,
	              species: str,
	              hp: int,
	              dodge: float,
	              prot: float,
	              spd: float,
	              cell_index: int) -> str:
		assert config.min_hp <= hp <= config.max_hp, f'Invalid hp value: {hp}; should be between {config.min_hp} and  {config.max_hp}.'
		assert config.min_dodge <= dodge <= config.max_dodge, f'Invalid dodge value: {dodge}; should be between {config.min_dodge} and  {config.max_dodge}.'
		assert config.min_prot <= prot <= config.max_prot, f'Invalid prot value: {prot}; should be between {config.min_prot} and  {config.max_prot}.'
		assert config.min_spd <= spd <= config.max_spd, f'Invalid spd value: {spd}; should be between {config.min_spd} and  {config.max_spd}.'
		encounter = get_encounter(level, room_name, cell_index)
		assert name not in [enemy.name for enemy in encounter.entities[
			EntityEnum.ENEMY.value]], f'Could not add enemy: {name} already exists in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
		assert len(encounter.entities.get(EntityEnum.ENEMY.value,
		                                  [])) < config.max_enemies_per_encounter, f'Could not add enemy: there are already {config.max_enemies_per_encounter} enemy(es) in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}, which is the maximum number allowed.'
		enemy = Enemy(name=name, description=description, species=species, hp=hp, dodge=dodge, prot=prot, spd=spd)
		encounter.add_entity(EntityEnum.ENEMY, enemy)
		return f'Added {name} to {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
	
	
	@AILibFunction(name='add_treasure', description='Add a treasure to a room or corridor',
	               required=['room_name', 'cell_index', 'name', 'description', 'loot'])
	@LibParam(room_name='The room (or corridor) name')
	@LibParam(
		cell_index='The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor.')
	@LibParam(name='The name of the treasure')
	@LibParam(description='The physical characteristics of the treasure')
	@LibParam(loot='The description of the loot in the treasure')
	def add_treasure(self, level: Level,
	                 room_name: str,
	                 name: str,
	                 description: str,
	                 loot: str,
	                 cell_index: int) -> str:
		encounter = get_encounter(level, room_name, cell_index)
		assert name not in [treasure.name for treasure in encounter.entities[
			EntityEnum.TREASURE.value]], f'Could not add treasure: {name} already exists in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
		assert 0 <= len(encounter.entities.get(EntityEnum.TREASURE.value,
		                                      [])) < config.max_treasures_per_encounter, f'Could not add treasure: there is already {config.max_treasures_per_encounter} treasure(s) in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}, which is the maximum number allowed..'
		treasure = Treasure(name=name, description=description, loot=loot)
		encounter.add_entity(EntityEnum.TREASURE, treasure)
		return f'Added {name} to {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
	
	
	@AILibFunction(name='add_trap',
	               description='Add a trap to a corridor cell. Traps can be added only to corridors, not to rooms.',
	               required=['corridor_name', 'cell_index', 'name', 'description', 'effect', 'cell_index'])
	@LibParam(corridor_name='The corridor name')
	@LibParam(cell_index='The corridor cell. Set to a value between 1 and the length of the corridor.')
	@LibParam(name='The name of the trap')
	@LibParam(description='The physical characteristics of the trap')
	@LibParam(effect='The effect of the trap')
	def add_trap(self, level: Level,
	             corridor_name: str,
	             name: str,
	             description: str,
	             effect: str,
	             cell_index: int) -> str:
		assert is_corridor(
			corridor_name), f'Traps can only be added only to corridors, but {corridor_name} seems to be a room.'
		corridor = level.get_corridor(*derive_rooms_from_corridor_name(corridor_name), ordered=False)
		assert corridor is not None, f'Corridor {corridor_name} does not exist.'
		assert 0 < cell_index <= corridor.length, f'{corridor_name} is a corridor, but cell_index={cell_index} is invalid, it should be a value between 1 and {corridor.length} (inclusive).'
		encounter = corridor.encounters[cell_index - 1]
		assert name not in [trap.name for trap in encounter.entities[
			EntityEnum.TRAP.value]], f'Could not add trap: {name} already exists in {corridor_name} in cell {cell_index}.'
		assert 0 <= len(encounter.entities.get(EntityEnum.TRAP.value,
		                                      [])) < config.max_traps_per_encounter, f'Could not add trap: there is already {config.max_traps_per_encounter} trap(s) in {corridor_name} in cell {cell_index}.'
		trap = Trap(name=name, description=description, effect=effect)
		encounter.add_entity(EntityEnum.TRAP, trap)
		return f'Added {name} in {corridor_name} in cell {cell_index}.'
	
	
	@AILibFunction(name='update_enemy_properties',
	               description="Update properties of an enemy in a room or corridor. Pass the current properties if they're not being updated.",
	               required=['room_name', 'cell_index', 'reference_name', 'name', 'description', 'species', 'hp',
	                         'dodge', 'prot', 'spd'])
	@LibParam(room_name='The room (or corridor) name')
	@LibParam(
		cell_index='The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor.')
	@LibParam(reference_name='The reference name of the enemy to update')
	@LibParam(name='The unique updated name of the enemy')
	@LibParam(description='The unique updated physical characteristics of the enemy')
	@LibParam(species='The updated species of the enemy')
	@LibParamSpec(name='hp',
	              description=f'The health points of the enemy, the value must be between {config.min_hp} and {config.max_hp}.')
	@LibParamSpec(name='dodge',
	              description=f'The dodge points of the enemy, the value must be between {config.min_dodge} and {config.max_dodge}.')
	@LibParamSpec(name='prot',
	              description=f'The protection points of the enemy, the value must be between {config.min_prot} and {config.max_prot}.')
	@LibParamSpec(name='spd',
	              description=f'The speed points of the enemy, the value must be between {config.min_spd} and {config.max_spd}.')
	def update_enemy_properties(self, level: Level,
	                            room_name: str,
	                            reference_name: str,
	                            name: str,
	                            description: str,
	                            species: str,
	                            hp: int,
	                            dodge: float,
	                            prot: float,
	                            spd: float,
	                            cell_index: int) -> str:
		assert config.min_hp <= hp <= config.max_hp, f'Invalid hp value: {hp}; should be between {config.min_hp} and {config.max_hp}.'
		assert config.min_dodge <= dodge <= config.max_dodge, f'Invalid dodge value: {dodge}; should be between {config.min_dodge} and {config.max_dodge}.'
		assert config.min_prot <= prot <= config.max_prot, f'Invalid prot value: {prot}; should be between {config.min_prot} and {config.max_prot}.'
		assert config.min_spd <= spd <= config.max_spd, f'Invalid spd value: {spd}; should be between {config.min_spd} and {config.max_spd}.'
		encounter = get_encounter(level, room_name, cell_index)
		assert reference_name in [enemy.name for enemy in encounter.entities[
			EntityEnum.ENEMY.value]], f'{reference_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
		assert (reference_name == name) or (name not in [enemy.name for enemy in encounter.entities[
			EntityEnum.ENEMY.value]]), f'{name} already exists in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
		updated_enemy = Enemy(name=name, description=description, species=species,
		                      hp=hp, dodge=dodge, prot=prot, spd=spd)
		encounter.replace_entity(reference_name, EntityEnum.ENEMY, updated_enemy)
		return f'Updated {reference_name} properties in {room_name}.'
	
	
	@AILibFunction(name='update_treasure_properties',
	               description="Update properties of a treasure in a room or corridor. Pass the current properties if they're not being updated.",
	               required=['room_name', 'cell_index', 'reference_name', 'name', 'description', 'loot'])
	@LibParam(room_name='The room (or corridor) name')
	@LibParam(
		cell_index='The corridor cell. Set to None when targeting a room, otherwise set to a value between 1 and the length of the corridor.')
	@LibParam(reference_name='The reference name of the treasure to update')
	@LibParam(name='The updated name of the treasure')
	@LibParam(description='The updated physical characteristics of the treasure')
	@LibParam(loot='The updated loot description of the treasure')
	def update_treasure_properties(self, level: Level,
	                               room_name: str,
	                               reference_name: str,
	                               name: str,
	                               description: str,
	                               loot: str,
	                               cell_index: int) -> str:
		encounter = get_encounter(level, room_name, cell_index)
		assert reference_name in [treasure.name for treasure in encounter.entities[
			EntityEnum.TREASURE.value]], f'{reference_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
		assert (reference_name == name) or (name not in [treasure.name for treasure in encounter.entities[
			EntityEnum.TREASURE.value]]), f'{name} already exists in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
		updated_treasure = Treasure(name=name, description=description, loot=loot)
		encounter.replace_entity(reference_name, EntityEnum.TREASURE, updated_treasure)
		return f'Updated {reference_name} properties in {room_name}.'
	
	
	@AILibFunction(name='update_trap_properties',
	               description="Update properties of a trap in a corridor. Pass the current properties if they're not being updated.",
	               required=['corridor_name', 'cell_index', 'reference_name', 'name', 'description', 'effect'])
	@LibParam(corridor_name='The corridor name')
	@LibParam(
		cell_index='The corridor cell. Set it to a value between 1 and the length of the corridor.')
	@LibParam(reference_name='The reference name of the trap to update')
	@LibParam(name='The updated name of the traps')
	@LibParam(description='The updated physical characteristics of the trap')
	@LibParam(effect='The updated effects descriptions of the trap')
	def update_trap_properties(self, level: Level,
	                           corridor_name: str,
	                           reference_name: str,
	                           name: str,
	                           description: str,
	                           effect: str,
	                           cell_index: int = None) -> str:
		corridor = level.get_corridor(*derive_rooms_from_corridor_name(corridor_name), ordered=False)
		assert corridor is not None, f'Corridor {corridor_name} does not exist.'
		assert 0 < cell_index <= corridor.length, f'{corridor_name} is a corridor, but cell_index={cell_index} is invalid, it should be a value between 1 and {corridor.length} (inclusive).'
		encounter = corridor.encounters[cell_index - 1]
		assert reference_name in [trap.name for trap in encounter.entities[
			EntityEnum.TRAP.value]], f'{reference_name} does not exist in {corridor_name} in cell {cell_index}.'
		assert (reference_name == name) or (name not in [trap.name for trap in encounter.entities[
			EntityEnum.TRAP.value]]), f'{name} already exists in {corridor_name} in cell {cell_index}.'
		updated_trap = Trap(name=name, description=description, effect=effect)
		encounter.replace_entity(reference_name, EntityEnum.TRAP, updated_trap)
		return f'Updated {reference_name} properties in {corridor_name}.'
	
	
	@AILibFunction(name='remove_entity',
	               description="Remove an entity (an enemy, a trap, or a treasure) from a room or corridor",
	               required=['room_name', 'cell_index', 'entity_name', 'entity_type'])
	@LibParam(room_name='The room (or corridor) name')
	@LibParam(
		cell_index='The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor.')
	@LibParam(entity_name='The name of the entity')
	@LibParam(entity_type='The type of the entity; must be of "enemy", "trap", or "treasure"')
	def remove_entity(self, level: Level,
	                  room_name: str,
	                  entity_name: str,
	                  entity_type: str,
	                  cell_index: int) -> str:
		entity_enum = get_enum_by_value(EntityEnum, entity_type)
		assert entity_enum is not None, f'Invalid entity type: {entity_type}.'
		encounter = get_encounter(level, room_name, cell_index)
		assert entity_name in [entity.name for entity in encounter.entities[
			entity_enum.value]], f'{entity_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
		encounter.remove_entity_by_name(entity_enum, entity_name)
		return f'Removed {entity_name} from {room_name}.'
	
	
	@AILibFunction(name='add_attack', description='Add an attack to an enemy.',
	               required=['room_name', 'cell_index', 'enemy_name', 'name', 'description', 'starting_positions',
	                         'target_positions', 'base_dmg'])
	@LibParam(room_name='The room (or corridor) name')
	@LibParam(
		cell_index='The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor.')
	@LibParam(enemy_name='The unique name of the enemy.')
	@LibParam(name='The unique name of the attack.')
	@LibParam(description='The description of the attack.')
	@LibParam(
		starting_positions='A string of 4 characters describing the positions from which the attack can be executed. Use "X" where the attack can be executed from, and "O" otherwise.')
	@LibParam(
		target_positions='A string of 4 characters describing the positions that the attack strikes to. Use "X" where the attack strikes to, and "O" otherwise.')
	@LibParamSpec(name='base_dmg',
	              description=f'The base damage of the attack. Must be between {config.min_base_dmg} and {config.max_base_dmg}.')
	def add_attack(self, level: Level,
	               room_name: str,
	               cell_index: int,
	               enemy_name: str,
	               name: str,
	               description: str,
	               starting_positions: str,
	               target_positions: str,
	               base_dmg: float) -> str:
		assert config.min_base_dmg <= base_dmg <= config.max_base_dmg, f'Invalid base_dmg value: {base_dmg}; should be between {config.min_base_dmg} and {config.max_base_dmg}.'
		encounter = get_encounter(level, room_name, cell_index)
		assert len(
			starting_positions) == 4, f'Invalid starting_positions value: {starting_positions}. Must be 4 characters long.'
		assert len(
			target_positions) == 4, f'Invalid target_positions value: {target_positions}. Must be 4 characters long.'
		assert set(starting_positions).issubset({'X', 'O'}), f'Invalid starting_positions value: {starting_positions}. Must contain only "X" and "O" characters.'
		assert set(target_positions).issubset({'X', 'O'}), f'Invalid target_positions value: {target_positions}. Must contain only "X" and "O" characters.'
		assert enemy_name in [entity.name for entity in encounter.entities[
			EntityEnum.ENEMY.value]], f'{enemy_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
		enemy: Enemy = encounter.entities[EntityEnum.ENEMY.value][
			[entity.name for entity in encounter.entities[EntityEnum.ENEMY.value]].index(enemy_name)]
		assert len(
			enemy.attacks) < config.max_num_attacks, f'Enemy {enemy.name} has {config.max_num_attacks}, which is the maximum amount allowed.'
		attack = Attack(name=name, description=description, starting_positions=starting_positions,
		                target_positions=target_positions, base_dmg=base_dmg)
		enemy.attacks.append(attack)
		return f'Added {name} to {enemy_name}.'
	
	
	@AILibFunction(name='update_attack',
	               description="Update an attack of an enemy. Pass the current properties if they're not being updated.",
	               required=['room_name', 'cell_index', 'enemy_name', 'reference_name', 'name', 'description',
	                         'starting_positions',
	                         'target_positions', 'base_dmg'])
	@LibParam(room_name='The room (or corridor) name')
	@LibParam(
		cell_index='The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor.')
	@LibParam(enemy_name='The unique name of the enemy.')
	@LibParam(reference_name='The reference name of the attack to update')
	@LibParam(name='The updated unique name of the attack.')
	@LibParam(description='The updated description of the attack.')
	@LibParam(
		starting_positions='The updated string of 4 characters describing the positions from which the attack can be executed. Use "X" where the attack can be executed from, and "O" otherwise.')
	@LibParam(
		target_positions='The updated string of 4 characters describing the positions that the attack strikes to. Use "X" where the attack strikes to, and "O" otherwise.')
	@LibParamSpec(name='base_dmg',
	              description=f'The updated base damage of the attack. Must be between {config.min_base_dmg} and {config.max_base_dmg}.')
	def update_attack(self, level: Level,
	                  room_name: str,
	                  cell_index: int,
	                  enemy_name: str,
	                  reference_name: str,
	                  name: str,
	                  description: str,
	                  starting_positions: str,
	                  target_positions: str,
	                  base_dmg: float) -> str:
		assert config.min_base_dmg <= base_dmg <= config.max_base_dmg, f'Invalid base_dmg value: {base_dmg}; should be between {config.min_base_dmg} and {config.max_base_dmg}.'
		encounter = get_encounter(level, room_name, cell_index)
		assert len(
			starting_positions) == 4, f'Invalid starting_positions value: {starting_positions}. Must be 4 characters long.'
		assert len(
			target_positions) == 4, f'Invalid target_positions value: {target_positions}. Must be 4 characters long.'
		assert set(starting_positions).issubset(set['X', 'O']), f'Invalid starting_positions value: {starting_positions}. Must contain only "X" and "O" characters.'
		assert set(starting_positions).issubset(set['X', 'O']), f'Invalid target_positions value: {target_positions}. Must contain only "X" and "O" characters.'
		assert enemy_name in [entity.name for entity in encounter.entities[
			EntityEnum.ENEMY.value]], f'{enemy_name} does not exist in {room_name}{" in cell " + str(cell_index) if cell_index != -1 else ""}.'
		enemy: Enemy = encounter.entities[EntityEnum.ENEMY.value][
			[entity.name for entity in encounter.entities[EntityEnum.ENEMY.value]].index(enemy_name)]
		assert reference_name in [attack.name for attack in
		                          enemy.attacks], f'{reference_name} is not an attack for {enemy_name}.'
		idx = [attack.name for attack in enemy.attacks].index(reference_name)
		attack = Attack(name=name, description=description, starting_positions=starting_positions,
		                target_positions=target_positions, base_dmg=base_dmg)
		enemy.attacks[idx] = attack
		return f'Updated {reference_name} of {enemy_name}.'
	
	
	@AILibFunction(name='remove_attack', description='Remove an attack from an enemy.',
	               required=['room_name', 'cell_index', 'enemy_name', 'name'])
	@LibParam(room_name='The room (or corridor) name')
	@LibParam(
		cell_index='The corridor cell. Set to -1 when targeting a room, otherwise set to a value between 1 and the length of the corridor.')
	@LibParam(enemy_name='The unique name of the enemy.')
	@LibParam(name='The unique name of the attack.')
	def remove_attack(self, level: Level,
	                  room_name: str,
	                  cell_index: int,
	                  enemy_name: str,
	                  name: str) -> str:
		encounter = get_encounter(level, room_name, cell_index)
		enemy: Enemy = encounter.entities[EntityEnum.ENEMY.value][
			[entity.name for entity in encounter.entities[EntityEnum.ENEMY.value]].index(enemy_name)]
		assert name in [attack.name for attack in enemy.attacks], f'{name} is not an attack for {enemy_name}.'
		idx = [attack.name for attack in enemy.attacks].index(name)
		enemy.attacks.pop(idx)
		return f'Removed {name} from {enemy_name}.'

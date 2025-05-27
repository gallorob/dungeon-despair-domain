import os
import pickle
from typing import Dict, Tuple, Optional, List

import PIL
from pydantic import BaseModel, Field

from dungeon_despair.domain.configs import config
from dungeon_despair.domain.corridor import Corridor
from dungeon_despair.domain.room import Room
from dungeon_despair.domain.utils import Direction


class Level(BaseModel):
	class Config:
		arbitrary_types_allowed = True
		use_enum_values = True

	rooms: Dict[str, Room] = Field(default={}, description="The rooms in the level.", required=True)
	corridors: Dict[str, Corridor] = Field(default={}, description="The corridors in the level.", required=True)
	connections: Dict[str, Dict[Direction, str]] = Field(default={}, description="The connections in the level.", required=True)
	
	current_room: str = Field(default='', description="The currently selected room.", required=True)
	
	def save_to_file(self, filename: str, conversation: str) -> None:
		all_images = os.listdir(config.temp_dir)
		images = {image_path: PIL.Image.open(os.path.join(config.temp_dir, image_path)) for image_path in all_images}
		bin_data = {
			'level': self,
			'images': images,
			'conversation': conversation
		}
		with open(filename, 'wb') as f:
			pickle.dump(bin_data, f)
	
	@staticmethod
	def load_from_file(filename: str) -> Tuple["Level", str]:
		with open(filename, 'rb') as f:
			bin_data = pickle.load(f)
			images = bin_data['images']
			for fpath, image in images.items():
				image.save(os.path.join(config.temp_dir, fpath))
			return bin_data['level'], bin_data['conversation']
	
	def export_level_as_scenario(self,
	                             filename: str) -> None:
		# get all sprites
		all_sprites = []
		for room in self.rooms.values():
			all_sprites.append(os.path.basename(room.sprite))
			for entity_type in room.encounter.entities.keys():
				for entity in room.encounter.entities[entity_type]:
					all_sprites.append(os.path.basename(entity.sprite))
		for corridor in self.corridors.values():
			all_sprites.extend([os.path.basename(x) for x in corridor.sprites])
			for encounter in corridor.encounters:
				for entity_type in encounter.entities.keys():
					for entity in encounter.entities[entity_type]:
						all_sprites.append(os.path.basename(entity.sprite))
		sprites = {sprite_path: PIL.Image.open(os.path.join(config.temp_dir, sprite_path)) for sprite_path in all_sprites}
		bin_data = {
			'level': self,
			'sprites': sprites,
		}
		with open(filename, 'wb') as f:
			pickle.dump(bin_data, f)
	
	@staticmethod
	def load_as_scenario(filename: str) -> "Level":
		with open(filename, 'rb') as f:
			bin_data = pickle.load(f)
			sprites = bin_data['sprites']
			for fpath, sprite in sprites.items():
				sprite.save(os.path.join(config.temp_dir, fpath))
			return bin_data['level']

	def __str__(self) -> str:
		# This is the GLOBAL level description
		level_description = 'Rooms:\n' + '\n'.join([str(self.rooms[k]) for k in self.rooms.keys()]) + '\n'
		level_description += 'Corridors:\n' + '\n'.join([str(self.corridors[k]) for k in self.corridors.keys()]) + '\n'
		level_description += f'Current room: {self.current_room}'
		return level_description
	
	def get_corridors_by_room(self, room_name) -> List[Corridor]:
		return [corridor for corridor in self.corridors.values() if corridor.room_from == room_name or corridor.room_to == room_name]
	
	def get_level_subset(self,
	                     corridor: Corridor,
	                     opposite_direction: bool = False) -> Tuple[List[Room], List[Corridor]]:
		# This method assumes that the corridor is NOT part of a loop
		rooms, corridors = [], []
		to_expand = [corridor.room_to] if not opposite_direction else [corridor.room_from]
		while len(to_expand) > 0:
			for area in to_expand:
				if area in self.rooms.keys():
					rooms.append(self.rooms[area])
					if opposite_direction:
						to_expand.extend([c.name for c in self.get_corridors_by_room(area) if c.room_from != area and c.name not in corridors])
					else:
						to_expand.extend([c.name for c in self.get_corridors_by_room(area) if c.room_to != area and c.name not in corridors])
				else:
					corridors.append(self.corridors[area])
					if self.corridors[area].room_to not in rooms:
						if opposite_direction:
							to_expand.append(self.corridors[area].room_from)
						else:
							to_expand.append(self.corridors[area].room_to)
				to_expand.remove(area)
		return rooms, corridors
	
	def remove_hanging_rooms(self,
						     ref_room: Optional[str] = None) -> None:
		ref_room = ref_room if ref_room is not None else self.current_room
		connected_rooms = [ref_room]
		has_more = True
		while has_more:
			has_more = False
			for room in connected_rooms:
				if room in self.connections.keys():
					for other_room in self.connections[room].values():
						if other_room != '' and other_room not in connected_rooms:
							connected_rooms.append(other_room)
							has_more = True
		all_rooms = list(self.rooms.keys())
		hanging_rooms = list(set(all_rooms).difference(set(connected_rooms)))
		for room in hanging_rooms:
			del self.rooms[room]
			del self.connections[room]
			for corridor in self.get_corridors_by_room(room):
				del self.corridors[corridor.name]
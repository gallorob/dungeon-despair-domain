import os
import pickle
from typing import Dict, Tuple, Optional, List

import PIL
from pydantic.v1 import BaseModel, Field

from dungeon_despair.domain.configs import config
from dungeon_despair.domain.corridor import Corridor
from dungeon_despair.domain.room import Room
from dungeon_despair.domain.utils import Direction


class Level(BaseModel):
	class Config:
		arbitrary_types_allowed = True

	rooms: Dict[str, Room] = Field(default={}, description="The rooms in the level.", required=True)
	corridors: Dict[str, Corridor] = Field(default={}, description="The corridors in the level.", required=True)
	connections: Dict[str, Dict[Direction, str]] = Field(default={}, description="The connections in the level.", required=True)
	
	current_room: str = Field(default='', description="The currently selected room.", required=True)
	
	def save_to_file(self, filename: str, conversation: str) -> None:
		# get all images
		all_images = []
		for room in self.rooms.values():
			all_images.append(room.sprite)
			for entity_type in room.encounter.entities.keys():
				for entity in room.encounter.entities[entity_type]:
					all_images.append(entity.sprite)
		for corridor in self.corridors.values():
			all_images.append(corridor.sprite)
			for encounter in corridor.encounters:
				for entity_type in encounter.entities.keys():
					for entity in encounter.entities[entity_type]:
						all_images.append(entity.sprite)
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

	def __str__(self) -> str:
		# This is the GLOBAL level description
		level_description = 'Rooms:\n' + '\n'.join([str(self.rooms[k]) for k in self.rooms.keys()]) + '\n'
		level_description += 'Corridors:\n' + '\n'.join([str(self.corridors[k]) for k in self.corridors.keys()]) + '\n'
		level_description += f'Current room: {self.current_room}'
		return level_description

	def get_corridor(self, room_from_name, room_to_name, ordered=False) -> Optional[Corridor]:
		c_name = f'{room_from_name}-{room_to_name}'
		corridor = self.corridors.get(c_name, None)
		if corridor is None and not ordered:
			c_name = f'{room_to_name}-{room_from_name}'
			corridor = self.corridors.get(c_name, None)
		return corridor
	
	def get_corridors_by_room(self, room_name) -> List[Corridor]:
		return [corridor for corridor in self.corridors.values() if corridor.room_from == room_name or corridor.room_to == room_name]
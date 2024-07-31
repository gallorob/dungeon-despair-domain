from typing import List

from pydantic.v1 import BaseModel, Field

from dungeon_despair.domain.configs import config
from dungeon_despair.domain.encounter import Encounter
from dungeon_despair.domain.utils import Direction


class Corridor(BaseModel):
	class Config:
		arbitrary_types_allowed = True
	
	room_from: str = Field(..., description="The room the corridor is connected to.", required=True)
	room_to: str = Field(..., description="The room the corridor is connects to.", required=True)
	direction: Direction = Field(Direction.NORTH, description="The direction of the corridor (room_from to room_to).",
	                             required=True)
	name: str = Field('', description='The name of the corridor.', required=True)
	length: int = Field(default=config.corridor_min_length, description="The length of the corridor", required=True)
	encounters: List[Encounter] = Field(default=[Encounter() for _ in range(config.corridor_min_length)],
	                                    description="The encounters in the corridor.", required=True)
	sprite: str = Field(default=None, description='The sprite for the corridor.', required=False)
	
	def __str__(self):
		s = f'{self.name}: from {self.room_from} to {self.room_to}, {self.length} cells long;'
		for i, e in enumerate(self.encounters):
			s += f'\nCell {i + 1} {str(e)}'
		return s

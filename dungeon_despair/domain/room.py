from pydantic.v1 import BaseModel, Field

from dungeon_despair.domain.encounter import Encounter


class Room(BaseModel):
	class Config:
		arbitrary_types_allowed = True

	name: str = Field(..., description="The name of the room.", required=True)
	description: str = Field(..., description="The description of the room", required=True)
	encounter: Encounter = Field(default=Encounter(), description='The encounter in the room.', required=True)
	sprite: str = Field(default=None, description='The sprite for the room.', required=False)

	def __str__(self):
		return f'{self.name}: {self.description};{self.encounter}'
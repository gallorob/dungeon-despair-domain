from pydantic import BaseModel, Field


class Entity(BaseModel):
	class Config:
		arbitrary_types_allowed = True
	
	name: str = Field(..., description="The name of the entity.", required=True)
	description: str = Field(..., description="The description of the entity.", required=True)
	sprite: str = Field(default=None, description='The sprite for the entity.', required=False)
	cost: int = Field(default=0, description='The cost to regenerate this entity.')
	
	def __str__(self):
		return f'{self.name}: {self.description}'

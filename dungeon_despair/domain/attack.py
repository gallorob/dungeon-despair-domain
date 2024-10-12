from pydantic import BaseModel, Field


class Attack(BaseModel):
	class Config:
		arbitrary_types_allowed = True
	
	name: str = Field(..., description="The name of the attack.", required=True)
	description: str = Field(..., description='The description of the attack', required=True)
	starting_positions: str = Field(..., description='The starting positions of the attack', required=True)
	target_positions: str = Field(..., description='The positions targeted by the attack', required=True)
	base_dmg: int = Field(..., description='The base attack damage', required=True)
	active: bool = Field(default=True, description='Whether the attack can be executed', required=False)
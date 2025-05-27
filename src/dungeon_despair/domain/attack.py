from typing import Optional
from pydantic import BaseModel, Field

from dungeon_despair.domain.modifier import Modifier
from dungeon_despair.domain.utils import ActionType


class Attack(BaseModel):
	class Config:
		arbitrary_types_allowed = True
		use_enum_values = True
	
	name: str = Field(..., description="The name of the attack.", required=True)
	description: str = Field(..., description='The description of the attack', required=True)
	type: ActionType = Field(..., description='The attack type: must be one of "damage" or "heal".')
	starting_positions: str = Field(..., description='The starting positions of the attack', required=True)
	target_positions: str = Field(..., description='The positions targeted by the attack', required=True)
	base_dmg: float = Field(..., description='The base attack damage. Use a negative value for "heal" attacks to indicate the amount of HP that can be recovered.', required=True)
	accuracy: float = Field(..., description='The attack accuracy (a percentage between 0.0 and 1.0).')
	active: bool = Field(default=True, description='Whether the attack can be executed', required=False)
	modifier: Optional[Modifier] = Field(None, description="The modifier the attack could have on the target.", required=False)
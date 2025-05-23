from typing import Literal, Optional
from pydantic import Field

from dungeon_despair.domain.entities.entity import Entity
from dungeon_despair.domain.modifier import Modifier


class Trap(Entity):
	effect: str = Field(..., description="The effect of the trap.", required=True)
	chance: float = Field(..., description="The chance this trap gets triggered", required=True)
	dmg: float = Field(..., description="The instant damage this trap deals to the hero once triggered", required=True)
	modifier: Optional[Modifier] = Field(None, description="The modifier the trap could apply to the hero once triggered", required=False)
	
	type: Literal["trap"]

	def __str__(self):
		return f'{super().__str__()} Effect={self.effect} Chance={self.chance} DMG={self.dmg} Modifier={self.modifier}'
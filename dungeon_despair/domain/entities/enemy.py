from typing import List

from pydantic import Field

from dungeon_despair.domain.attack import Attack
from dungeon_despair.domain.entities.entity import Entity
from dungeon_despair.domain.modifier import Modifier


class Enemy(Entity):
	species: str = Field(..., description="The enemy species.", required=True)
	hp: float = Field(..., description="The enemy HP.", required=True)
	max_hp: float = Field(..., description="The enemy max HP")
	dodge: float = Field(..., description="The enemy dodge stat.", required=True)
	prot: float = Field(..., description="The enemy prot stat.", required=True)
	spd: float = Field(..., description="The enemy spd stat.", required=True)
	attacks: List[Attack] = Field([], description='The enemy attacks', required=True)
	modifiers: List[Modifier] = Field([], description="The enemy's modifiers", required=True)
	
	def __str__(self):
		return f'{super().__str__()} Species={self.species} HP={self.hp} DODGE={self.dodge} PROT={self.prot} SPD={self.spd}'

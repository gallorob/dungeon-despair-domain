from typing import List

from pydantic import Field

from dungeon_despair.domain.attack import Attack
from dungeon_despair.domain.entities.entity import Entity


class Hero(Entity):
	species: str = Field("Human", description="The hero species.", required=True)
	hp: float = Field(..., description="The hero HP.", required=True)
	dodge: float = Field(..., description="The hero dodge stat.", required=True)
	prot: float = Field(..., description="The hero prot stat.", required=True)
	spd: float = Field(..., description="The hero spd stat.", required=True)
	stress: int = Field(0, description="The hero stress.", required=True)
	attacks: List[Attack] = Field([], description='The hero attacks', required=True)

	def __str__(self):
		return f'Hero {super().__str__()} Species={self.species} HP={self.hp} DODGE={self.dodge} PROT={self.prot} SPD={self.spd}'

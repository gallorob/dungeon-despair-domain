from typing import List, Literal

from pydantic import Field

from dungeon_despair.domain.attack import Attack
from dungeon_despair.domain.entities.entity import Entity
from dungeon_despair.domain.modifier import Modifier


class Hero(Entity):
	species: str = Field("Human", description="The hero species.", required=True)
	hp: float = Field(..., description="The hero HP.", required=True)
	dodge: float = Field(..., description="The hero dodge stat.", required=True)
	prot: float = Field(..., description="The hero prot stat.", required=True)
	spd: float = Field(..., description="The hero spd stat.", required=True)
	stress: int = Field(0, description="The hero stress.", required=True)
	attacks: List[Attack] = Field([], description='The hero attacks', required=True)
	
	trap_resist: float = Field(..., description="The chance this hero will not trigger traps", required=True)
	stress_resist: float = Field(..., description="The percentage resistance of the hero to stress", required=True)
	
	modifiers: List[Modifier] = Field([], description="The hero's modifiers", required=True)
	
	max_hp: float = Field(-1, description="The hero max HP")

	type: Literal["hero"] = Field("hero", required=True)
	
	def __str__(self):
		return f'{super().__str__()} Species={self.species} HP={self.hp} DODGE={self.dodge} PROT={self.prot} SPD={self.spd}'

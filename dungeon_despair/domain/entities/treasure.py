from pydantic import Field

from dungeon_despair.domain.entities.entity import Entity
from dungeon_despair.domain.modifier import Modifier


class Treasure(Entity):
	loot: str = Field(..., description="The loot in the treasure.", required=True)
	trapped_chance: float = Field(..., description="The chance that this treasure's trap gets triggered", required=True)
	dmg: float = Field(..., description="The damage this treasure deals to a hero if the internal trap is triggered", required=True)
	modifier: Modifier = Field(None, description="The modifier the treasure could apply to the hero if the internal trap is triggered", required=False)
	
	def __str__(self):
		return f'{super().__str__()} Loot={self.loot} Trapped Chance={self.trapped_chance} DMG={self.dmg} Modifier={str(self.modifier)}'
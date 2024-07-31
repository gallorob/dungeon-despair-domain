from pydantic.v1 import Field

from dungeon_despair.domain.entities.entity import Entity


class Treasure(Entity):
	loot: str = Field(..., description="The loot in the treasure.", required=True)

	def __str__(self):
		return f'Treasure {super().__str__()} Loot={self.loot}'
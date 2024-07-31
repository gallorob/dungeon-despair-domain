from pydantic.v1 import Field

from dungeon_despair.domain.entities.entity import Entity


class Trap(Entity):
	effect: str = Field(..., description="The effect of the trap.", required=True)

	def __str__(self):
		return f'Trap {super().__str__()} Effect={self.effect}'
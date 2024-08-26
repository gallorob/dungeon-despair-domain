from typing import Dict, List, Union

from pydantic.v1 import BaseModel, Field

from dungeon_despair.domain.entities.enemy import Enemy
from dungeon_despair.domain.entities.trap import Trap
from dungeon_despair.domain.entities.treasure import Treasure
from dungeon_despair.domain.utils import EntityEnum


class Encounter(BaseModel):
	class Config:
		arbitrary_types_allowed = True

	entities: Dict[str, List[Union[Enemy, Trap, Treasure]]] = Field(
		default={k: [] for k in [EntityEnum.ENEMY.value, EntityEnum.TRAP.value, EntityEnum.TREASURE.value]},
		description="The entities for this encounter.", required=True)

	def __str__(self):
		s = ''
		for k in self.entities.keys():
			s += f'\n\t{str(k).lower()}: {"; ".join(str(self.entities[k]))}'
		return s

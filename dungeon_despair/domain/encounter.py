from typing import Dict, List, Union

from pydantic.v1 import BaseModel, Field

from dungeon_despair.domain.entities.enemy import Enemy
from dungeon_despair.domain.entities.entity import Entity
from dungeon_despair.domain.entities.trap import Trap
from dungeon_despair.domain.entities.treasure import Treasure
from dungeon_despair.domain.utils import EntityClass, entityclass_thresolds


class Encounter(BaseModel):
	class Config:
		arbitrary_types_allowed = True

	entities: Dict[str, List[Union[Enemy, Trap, Treasure]]] = Field(
		default={k: [] for k in [EntityClass.ENEMY.name, EntityClass.TRAP.name, EntityClass.TREASURE.name]},
		description="The entities for this encounter.", required=True)

	def __str__(self):
		s = ''
		for k in self.entities.keys():
			s += f'\n\t{str(k).lower()}: {"; ".join(str(self.entities[k]))}'
		return s
	
	def try_add_entity(self, entity: Entity) -> bool:
		klass = EntityClass(entity.__class__)
		if klass not in self.entities.keys(): self.entities[klass.name] = []
		if len(self.entities[klass.name]) < entityclass_thresolds[klass]:
			for other_entity in self.entities[klass.name]:
				if other_entity.name == entity.name:
					return False
			# add the entity
			self.entities[klass.name].append(entity)
			return True
		return False
	
	def try_remove_entity(self, entity_name: str, entity_type: str) -> bool:
		n = None
		for i, entity in enumerate(self.entities[entity_type]):
			if entity.name == entity_name:
				n = i
				break
		if n is not None:
			self.entities[entity_type].pop(n)
			return True
		return False
	
	def try_update_entity(self, entity_reference_name: str, entity_reference_type: str, updated_entity: Entity) -> bool:
		# TODO: Updating names of entities should be checked against existing names of entities in the same room!
		for i, entity in enumerate(self.entities[entity_reference_type]):
			if entity.name == entity_reference_name:
				if updated_entity.description == self.entities[entity_reference_type][i].description:
					updated_entity.sprite = self.entities[entity_reference_type][i].sprite
				self.entities[entity_reference_type][i] = updated_entity
				return True
		return False
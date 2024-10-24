from typing import Dict, List

from pydantic import BaseModel, Field

from dungeon_despair.domain.entities.entity import Entity
from dungeon_despair.domain.utils import EntityEnum


class Encounter(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    entities: Dict[str, List[Entity]] = Field(
        default={k.value: [] for k in EntityEnum},
        description="The entities for this encounter.", required=True)

    def __str__(self):
        s = ''
        for k in self.entities.keys():
            s += f'\n\t{str(k).lower()}: {"; ".join([str(x) for x in self.entities[k]])}'
        return s

    def add_entity(self,
                   entity_type: EntityEnum,
                   entity: Entity) -> None:
        self.entities[entity_type.value].append(entity)

    def replace_entity(self,
                       ref_name: str,
                       entity_type: EntityEnum,
                       new_entity: Entity) -> None:
        idx = [entity.name for entity in self.entities[entity_type.value]].index(ref_name)
        prev_entity = self.entities[entity_type.value][idx]
        if prev_entity.description == new_entity.description:
            new_entity.sprite = prev_entity.sprite
        self.entities[entity_type.value][idx] = new_entity

    def remove_entity_by_name(self,
                              entity_type: EntityEnum,
                              entity_name: str) -> None:
        idx = [entity.name for entity in self.entities[entity_type.value]].index(entity_name)
        self.entities[entity_type.value].pop(idx)

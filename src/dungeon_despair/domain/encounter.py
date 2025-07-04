from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from dungeon_despair.domain.configs import config

from dungeon_despair.domain.entities.enemy import Enemy
from dungeon_despair.domain.entities.entity import Entity
from dungeon_despair.domain.entities.trap import Trap
from dungeon_despair.domain.entities.treasure import Treasure
from dungeon_despair.domain.utils import EntityEnum


EntityItem = Annotated[Enemy | Trap | Treasure, Field(discriminator="type")]


class Encounter(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    entities: Dict[str, List[EntityItem]] = Field(
        default={k.value: [] for k in EntityEnum},
        description="The entities for this encounter.",
        required=True,
    )

    def __str__(self):
        s = ""
        for k in self.entities.keys():
            s += (
                f'\n\t{str(k).lower()}: {"; ".join([str(x) for x in self.entities[k]])}'
            )
        return s

    def add_entity(self, entity_type: EntityEnum, entity: Entity) -> None:
        self.entities[entity_type.value].append(entity)

    def replace_entity(
        self, ref_name: str, entity_type: EntityEnum, new_entity: Entity
    ) -> None:
        idx = [entity.name for entity in self.entities[entity_type.value]].index(
            ref_name
        )
        prev_entity = self.entities[entity_type.value][idx]
        if prev_entity.description == new_entity.description:
            new_entity.sprite = prev_entity.sprite
        self.entities[entity_type.value][idx] = new_entity

    def remove_entity_by_name(self, entity_type: EntityEnum, entity_name: str) -> None:
        idx = [entity.name for entity in self.entities[entity_type.value]].index(
            entity_name
        )
        self.entities[entity_type.value].pop(idx)

    def get_entity_by_name(
        self, entity_type: EntityEnum, entity_name: str
    ) -> Optional[Entity]:
        names = [entity.name for entity in self.entities[entity_type.value]]
        if entity_name in names:
            idx = names.index(entity_name)
            return self.entities[entity_type.value][idx]
        return None

    @property
    def enemies(self) -> List[Enemy]:
        return self.entities["enemy"]

    @property
    def traps(self) -> List[Trap]:
        return self.entities["trap"]

    @property
    def treasures(self) -> List[Treasure]:
        return self.entities["treasure"]

    @property
    def cost(self) -> float:
        # The cost of the encounter is the cost of the base encounter plus the sum of the costs of all entities in the encounter

        return config.encounter_cost + sum(
            entity.cost
            for entity_list in self.entities.values()
            for entity in entity_list
        )

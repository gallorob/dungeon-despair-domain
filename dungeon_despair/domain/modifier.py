from pydantic import BaseModel, Field

from dungeon_despair.domain.utils import ModifierType, get_enum_by_value


class Modifier(BaseModel):
	class Config:
		arbitrary_types_allowed = True
		use_enum_values = True
	
	type: ModifierType = Field(..., description=f"The modifier type: must be one of {', '.join([x.value for x in ModifierType])}.", required=True)
	chance: float = Field(..., description="The chance that this modifier is applied to the target.", requred=True)
	turns: int = Field(-1, description="The number of turns this modifier is applied for.", requred=True)
	amount: float = Field(0.0, description="The amount this modifier applies.", requred=True)
	
	def __str__(self):
		type_enum = get_enum_by_value(ModifierType, self.type)
		if type_enum == ModifierType.STUN:
			return f'Stun for {self.turns} turns.'
		elif type_enum == ModifierType.BLEED:
			return f'Bleed for {self.turns} turns (-{self.amount}HP/turn).'
		elif type_enum == ModifierType.SCARE:
			return f'Scare for {self.turns} (-{self.amount:.0%} stress resist)'
		elif type_enum == ModifierType.HEAL:
			return f'Heal for {self.turns} turns (+{self.amount}HP/turn).)'
		else:
			return f'{self.type}: {self.amount} x{self.turns}'
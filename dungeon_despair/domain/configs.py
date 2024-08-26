from argparse import Namespace


class Config(Namespace):
	corridor_min_length: int = 2
	corridor_max_length: int = 4
	
	max_enemies_per_encounter: int = 4
	max_traps_per_encounter: int = 1
	max_treasures_per_encounter: int = 1
	
	min_hp: int = 1
	max_hp: int = 20
	min_dodge: float = 0.1
	max_dodge: float = 1.0
	min_prot: float = 0.0
	max_prot: float = 1.0
	min_spd: float = 0.1
	max_spd: float = 1.0
	
	temp_dir: str = './temp_assets'


config = Config()
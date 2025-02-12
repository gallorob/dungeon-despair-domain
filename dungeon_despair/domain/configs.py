from argparse import Namespace


class Config(Namespace):
    corridor_min_length: int = 2
    corridor_max_length: int = 4

    max_enemies_per_encounter: int = 4
    max_traps_per_encounter: int = 1
    max_treasures_per_encounter: int = 1

    min_hp: int = 1.0
    max_hp: int = 20.0
    min_dodge: float = 0.01
    max_dodge: float = 0.99
    min_prot: float = 0.01
    max_prot: float = 0.99
    min_spd: float = 0.1
    max_spd: float = 1.0

    max_num_attacks: int = 4
    min_base_dmg: float = 0.0
    max_base_dmg: float = 5.0

    temp_dir: str = './temp_assets'


config = Config()

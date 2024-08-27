# Dungeon Despair Domain

This repository contains the domain definitions and functions for Large Language Models function calling in OpenAI's-compatible format.

Dungeon Despair is used as:
* A video-game, available [here](https://github.com/gallorob/dungeon-despair)
* A domain for LLMaker, a natural-language based design assistant, available [here](https://github.com/gallorob/llmaker)

## Domain Description
A `Level` in the dungeon is comprised of `Room`s and `Corridor`s. Each `Room` can have a maximum of 4 `Corridor`s (one per cardinal direction). Within a `Room` or a `Corridor` there are `Encounter`s. A `Room` only has a single `Encounter`, whereas a `Corridor` has as many `Encounter`s as its length (in cells).

An `Encounter` can be empty, or can contain one or more of the following entities: `Enemy`, `Trap`, and `Treasure`. A `Trap` can only be found in a `Corridor`, whether the other two entities can be found in either a `Room` or a `Corridor`.

All parameters that define the level can be tweaked in `domain/configs.py`.

Editing the level can be achieved by executing the relevant functions in `functions.py` (or letting an LLM do it for you 😉). `Hero`es are currently not supported for generation.

## Install Dungeon Despair Domain
Dungeon Despair Domain is provided as a Python package. First, create a virtual environment with the version of Python you're going to use and activate it (recommended version is 3.10). 
Simply clone the repository
```bash
git clone https://github.com/gallorob/dungeon-despair-domain & cd dungeon-despair-domain
```
Then install the package locally:
```bash
pip install -e .
```
Alternatively, you can define this repository as requirement for your Python project by adding
```markdown
git+https://github.com/gallorob/dungeon-despair-domain.git
```

## Citing Dungeon Despair Domain
If you use Dungeon Despair Domain in your publication, please cite it by using the following BibTeX entry:
```bibtex
@Misc{dungeon_despair_domain,
  title =        {Dungeon Despair Domain: Designing Complete Dungeons With LLMs},
  author =       {Roberto Gallotta},
  howpublished = {\url{https://github.com/gallorob/dungeon-despair-domain}},
  year =         {2024}
}
```

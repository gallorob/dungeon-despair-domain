from setuptools import setup

setup(name='dungeon_despair_domain',
      author='Roberto Gallotta',
      author_email='roberto.gallotta@um.edu.mt',
      description='Dungeon Despair Domain',
      long_description='',
      version='0.0.1',
      python_requires='>=3.11',
      install_requires=['pydantic', 'pyyaml', 'gptfunctionutil'],
      packages=['dungeon_despair'],
      )
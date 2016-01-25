from setuptools import setup, find_packages


# Normal setup stuff
setup(
    name='mush',
    install_requires=['prettytable'],
    packages=find_packages(),
    zip_safe=False,
    entry_points={
        'console_scripts':
        ['mush = mush.cli:entry_point']},
    )

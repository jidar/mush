from setuptools import setup, find_packages


# Normal setup stuff
setup(
    name='mush',
    description="multi-use-shell-helper...ok, I'll admit it's a backronymn :)",
    version='1.0.0',
    install_requires=['prettytable'],
    packages=find_packages(),
    zip_safe=False,
    entry_points={
        'console_scripts':
        ['mush = mush.cli:entry_point']},
    )

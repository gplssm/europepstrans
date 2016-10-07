from distutils.core import setup

setup(
    name='europepstrans',
    version='0.0.1-pre',
    packages=[''],
    url='',
    license='GPL v3',
    author='Guido Pleßmann',
    author_email='guido.plessmann@rl-institut.de',
    description='European power sector long-term investment model',
    install_requires=[
        'pandas >= 0.18.1',
        'matplotlib',
        'oemof >= 0.0.8.dev0']
)

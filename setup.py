import setuptools
from pathlib import Path

this_directory = Path(__file__).parent

# read the contents of README file
readme = (this_directory / 'README.md').read_text()

setuptools.setup(
    name='pwforecast',
    version='0.1.11',
    author='Tim Hawker',
    description='A Python module to charge/discharge Powerwall based on solar forecast and peak/off peak tariffs.',
    url='https://github.com/timhawker/pwforecast',
    long_description_content_type='text/markdown',
    long_description=readme,
    packages=['pwforecast'],
    install_requires=['tzlocal', 'requests', 'python-dateutil', 'TeslaPy']
)

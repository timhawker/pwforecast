import setuptools

# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setuptools.setup(
    name='pwforecast',
    version='0.1.4',
    author='Tim Hawker',
    description='A Python module to charge/discharge Powerwall based on solar forecast and peak/off peak tariffs.',
    url='https://github.com/timhawker/pwforecast',
    long_description_content_type='text/markdown',
    long_description=long_description
)
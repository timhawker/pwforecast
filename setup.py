import setuptools
from pathlib import Path

# read the contents of README file
this_directory = Path(__file__).parent
readme = (this_directory / 'README.md').read_text()

setuptools.setup(
    name='pwforecast',
    version='1.2.0',
    author='Tim Hawker',
    license='MIT',
    url='https://github.com/timhawker/pwforecast',
    description=('A Python module to charge/discharge Tesla Powerwall based '
                 'on solar forecast and peak/off peak tariffs.'),
    long_description_content_type='text/markdown',
    long_description=readme,
    py_modules=['pwforecast'],
    install_requires=['tzlocal', 'requests', 'python-dateutil', 'TeslaPy']
)

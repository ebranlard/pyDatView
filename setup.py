from setuptools import setup

setup(
    name='pydatview',
    version='0.5',
    description='GUI to display tabulated data from files or pandas dataframes',
    url='http://github.com/ebranlard/pyDatView/',
    author='Emmanuel Branlard',
    author_email='lastname@gmail.com',
    license='MIT',
    packages=['pydatview'],
    python_requires='>=3.9',
    install_requires=[
        'numpy>=2.0',
        'pandas>=2.2',
        'matplotlib>=3.8',
        'scipy>=1.12',
        'wxpython>=4.2.4',
        'openpyxl>=3.1',
        'xarray>=2024.1',
        'pyarrow>=15.0',
        'chardet>=5.0',
        'pyyaml>=6.0',
    ],
    zip_safe=False
)


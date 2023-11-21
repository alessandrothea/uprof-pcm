from setuptools import setup, find_packages

setup(
    name='uprofpcmserver',
    version='0.1.0',
    description='A uProf PCM server',
    author='Alessandro Thea',
    author_email='alessandro.thea@stfc.ac.uk',
    # url='https://blog.godatadriven.com/setup-py',
    packages=find_packages(include=['exampleproject', 'exampleproject.*']),
    install_requires=[
        'PyYAML',
        'pandas==0.23.3',
        'numpy>=1.14.5'
    ],
    extras_require={'plotting': ['matplotlib>=2.2.0', 'jupyter']},
    setup_requires=['pytest-runner', 'flake8'],
    tests_require=['pytest'],
    entry_points={
        'console_scripts': ['my-command=exampleproject.example:main']
    },
    package_data={'exampleproject': ['data/schema.json']}
)
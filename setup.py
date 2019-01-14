from setuptools import setup

setup(
    name='gcalendar',
    version='1.0',
    packages=['gcalendar'],
    description='A command line tool for Google Calendar using python',
    author='iCodeCoolStuff',
    license='MIT',
    install_requires=[
        'argparse',
        'click', 
        'google-api-python-client', 
        'oauth2client',
    ],
    entry_points={
        'console_scripts': [
            'gcalendar=gcalendar.gcalendar:cli'
        ],
    },
)

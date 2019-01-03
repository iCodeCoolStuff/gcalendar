from setuptools import setup

setup(
    name='gcalendar',
    description='A calendar tool for Google Calendar',
    url='#',
    author='iCodeCoolStuff',
    license='ISC',
    install_requires=[
        'click', 
        'google-api-python-client', 
        'oauth2client',
    ]
)

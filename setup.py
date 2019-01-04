from setuptools import setup

setup(
    name='gcalendar',
    version='0.1'
    pymodules=['gcalendar']
    description='A calendar tool for Google Calendar using python',
    author='iCodeCoolStuff',
    license='ISC',
    install_requires=[
        'click', 
        'google-api-python-client', 
        'oauth2client',
    ]
    entry_points='''
        [console_scripts]
        save:cli
    '''
)

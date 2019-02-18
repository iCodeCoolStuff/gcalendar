import calendar
import datetime
import json
import pathlib
import os
import pprint
import time
import re
import sys
import webbrowser

from copy import deepcopy

import argparse
import click

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

SCOPES = 'https://www.googleapis.com/auth/calendar'
FILE_DIRECTORY = str(pathlib.Path(__file__).parent)

#Start library

DATE_PATTERN          = re.compile(r'(\d{4})[:/.-](\d{1,2})[:/.-](\d{1,2})')
TIMESTAMP_PATTERN     = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-]\d{2}:\d{2})?')
RELATIVE_DATE_PATTERN = re.compile('(last|next)\s(\w+)', re.IGNORECASE)

WEEKDAYS = {
    'sunday':    0, 
    'monday':    1, 
    'tuesday':   2, 
    'wednesday': 3, 
    'thursday':  4, 
    'friday':    5, 
    'saturday':  6,
} 

def RFC_from_UTC(dt):
    '''Generates a timestamp according to RFC3339
   
    Parameters:
        dt (datetime.datetime): a datetime.datetime object

    Returns:
        str: a timestamp according to RFC3339
    '''
    return dt.isoformat() + 'Z'

def get_utc_offset():
    '''Returns the UTC offset of the current timezone in hours 

    Returns:
        int: The offset of the current timezone in hours
    '''
    return time.localtime().tm_gmtoff / 3600

def get_min_time(dt):
    '''Returns the very start of a certain date

    Parameters:
        dt (datetime.datetime): a datetime.datetime object

    Returns:
        datetime.datetime: a datetime.datetime object with its hours, 
            minutes, and seconds set to 0
    '''
    return datetime.datetime(dt.year, dt.month, dt.day, 0, 0, 0)

def get_max_time(dt):
    '''Returns the very end of a certain date

    Parameters:
        dt (datetime.datetime): a datetime.datetime object

    Returns:
        datetime.datetime: a datetime.datetime object with its hours,
            minutes, and seconds set to their maximum value
    '''
    return datetime.datetime(dt.year, dt.month, dt.day, 23, 59, 59)

def gmt(dt):
    '''Returns a datetime with its time set to GMT

    Parameters:
        dt (datetime.datetime): a datetime.datetime object

    Returns:
        datetime.datetime: a datetime.datetime object with its time
            in Greenwich Mean Time
    '''
    offset = get_utc_offset()
    if offset < 0:
        td = datetime.timedelta(hours=offset * -1)
        return dt + td 
    elif offset > 0:
        td = datetime.timedelta(hours=offset)
        return dt - td
    else:
        return dt

def utctimestamp_to_dt(timestamp):
    '''Returns a datetime.datetime object from a UTC timestamp

    Parameters:
        timestamp (str): A timestamp with UTC format

    Returns:
        datetime.datetime: a datetime.datetime object with the same time
            as the given timestamp
    '''
    date = re.match(TIMESTAMP_PATTERN, timestamp)
    return datetime.datetime(
            int(date.group(1)),
            int(date.group(2)),
            int(date.group(3)),
       hour=int(date.group(4)),
     minute=int(date.group(5)),
     second=int(date.group(6)))

def date_from_dt(dt):
    '''Returns a date of the form YYYY-MM-DD from a datetime.datetime object

    Parameters:
        dt (datetime.datetime): a datetime.datetime object

    Returns:
        str: a date of the form YYYY-MM-DD 
    '''
    return f'{dt.year}-{dt.month}-{dt.day}'

def get_events(service, dt):
    '''Returns a list of events from a given date   

    Parameters:
        service (googleapiclient.discovery.Resource): A Resource object that
            uses the Google Calendar v3 API
        dt (datetime.datetime): a datetime.datetime object

    Returns:
        list: a list of all event (JSON) objects from a given date
    '''
    mn, mx = get_min_and_max(dt)
    mintime = RFC_from_UTC(gmt(mn))
    maxtime = RFC_from_UTC(gmt(mx))
    result = service.events().list(calendarId='primary', timeMin=mintime, timeMax=maxtime,
                                    singleEvents=True, orderBy='startTime').execute()
    items = result.get('items', [])
    if not items:
        return None
    return items

def dt_to_POSIX(dt):
    '''Returns a POSIX timestamp from a datetime.datetime object

    Parameters:
        dt (datetime.datetime): a datetime.datetime object

    Returns:
        int: a POSIX timestamp for a specific point in time
    '''
    return calendar.timegm(dt.timetuple())

def get_start_and_end(event):
    '''Returns a tuple of the start and end of an event

    Parameters:
        event (dict): a dict representing an event object

    Returns:
        tuple: a tuple with the first index as the start 
            of an event and the second index as the end of an event
    '''
    s_timestamp = event['start']['dateTime']
    e_timestamp = event['end']['dateTime']

    start = utctimestamp_to_dt(s_timestamp)
    end   = utctimestamp_to_dt(e_timestamp)
    return (start, end)

def get_min_and_max(dt):
    '''Returns a tuple of the minimum and maximum of a date

    Parameters:
        dt (datetime.datetime): a datetime.datetime object

    Returns:
        tuple: a tuple with the first index as the minimum of a date and the
            second index as the maximum of a date
    '''
    mintime = get_min_time(dt)
    maxtime = get_max_time(dt)

    return (mintime, maxtime)

def get_days_of_week(dt):
    '''Returns a list of days corresponding to a week in time

    Order of days: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, 
        Saturday

    Parameters:
        dt (datetime.datetime): a datetime.datetime object

    Returns:
        list: a list of datetime.datetime objects corresponding to the days
            of a week from a given datetime.datetime object
    '''
    date = calendar.weekday(dt.year, dt.month, dt.day)
    if date == 6:
        days = []
        for i in range(7):
            days.append(datetime.datetime(dt.year, dt.month, dt.day+i))
        return days

    offset = 0
    while date != 6:
        offset -= 1 
        dt2 = dt + datetime.timedelta(days=offset)
        date = calendar.weekday(dt2.year, dt2.month, dt2.day)
    days = []
    for i in range(7):
        days.append(datetime.datetime(dt.year, dt.month, dt.day) + datetime.timedelta(days=(offset+i)))
    return days

def get_current_week():
    '''Returns a list of days representing the current week

    Order of days: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday,
        Saturday
    '''
    return get_days_of_week(datetime.datetime.today())

def get_day_range(dt1, dt2):
    '''Returns a list of datetime.datetime objects from dt1 to dt2 (inclusive)
    
    Parameters:
        dt1 (datetime.datetime): The starting datetime
        dt2 (datetime.datetime): The ending datetime
    Returns:
        list: a list of datetime objects corresponding to the range of dates
            between dt1 and dt2
    '''

    dt1 = datetime.datetime(dt1.year, dt1.month, dt1.day)
    dt2 = datetime.datetime(dt2.year, dt2.month, dt2.day)
    
    td = datetime.timedelta(days=1)
    dt_range = []
    current_dt = dt1
    while current_dt < dt2+td:
        dt_range.append(current_dt)
        current_dt += td
    return dt_range

def dt_from_date(date):
    '''Returns a datetime.datetime object from a date of the form YYYY-MM-DD 

    Parameters: 
        date (str): a date of the form YYYY-MM-DD

    Returns:
        datetime.datetime: a datetime.datetime object corresponding to the
            given date
    '''
    date = re.match(DATE_PATTERN, date)
    dt = datetime.datetime(
            int(date.group(1)),
            int(date.group(2)), 
            int(date.group(3)))
    return dt

def is_reldate(date):
    '''Returns whether or not a string is a "relative date"

    A "relative date" is a day of the week preceeded by either "next" or 
    "last". Does not include "yesterday" or "tomorrow".

    Parameters:
        date (str): a string that fits in the regular expression of 
        "(last|next)\s(\w+)" ignoring case

    Returns:
        bool: a Boolean telling whether or not the given string is a "relative
            date"
    '''
    reldate = re.match(RELATIVE_DATE_PATTERN, date)
    if reldate:
        if reldate.group(2) in WEEKDAYS.keys():
            return True
        return False
    return False

def dt_from_reldate(date):
    '''Returns a datetime.datetime object from a "relative date"

    Parameters:
        date (str): a string representing a "relative date"

    Returns:
        datetime.datetime: a datetime.datetime object representing a 
            "relative date"
    '''
    reldate = re.match(RELATIVE_DATE_PATTERN, date)
    dt = get_current_week()[WEEKDAYS[reldate.group(2)]]
    td = datetime.timedelta(weeks=1)
    if reldate.group(1).lower() == 'next':
        return dt + td 
    else:
        return dt - td

def clone_event(event):
    '''Returns a "clone" of an event object

    A "clone" is an event object but is completely stripped of whatever 
    that gives an event object its meaning (i.e. id, etag, iCalUID, 
    recurringEventId, and originalStartTime)

    This function does not modify the original event object

    Parameters:
        event (dict): a dict representing a Google Calendar event object

    Returns:
        dict: a "clone" of the given event object
    '''
    new_event = deepcopy(event)
    if new_event.get('id'):
        del new_event['id']
    if new_event.get('etag'):
        del new_event['etag']
    if new_event.get('iCalUID'):
        del new_event['iCalUID']
    if new_event.get('recurringEventId'):
        del new_event['recurringEventId']
    if new_event.get('originalStartTime'):
        del new_event['originalStartTime']
    return new_event

def clone_events(events):
    '''Clones a list of event objects

    This function calls the function clone_event on each event in events.
    It also does not modify the original event object
    
    Parameters:
        events (list): a list of Google Calendar event objects
    Returns:
        list: a list of cloned event objects
    '''

    new_events = []
    for event in events:
        new_events.append(clone_event(event))

    return new_events

def save_events(events, filename):
    '''Saves Google Calendar events to a JSON file

    Each Google Calendar object is cloned and saved to the specified JSON
    file

    Parameters:
        events (list): a list of Google Calendar event objects
        filename (str): a filename pointing to a JSON file
    '''
    new_events = []
    for event in events:
        new_events.append(clone_event(event))

    with open(filename, 'w') as f:
        json.dump(events, f)

def upload_events(service, events, dt):
    '''Uploads events to a given day on Google Calendar

    This function takes the difference between an event's starting time and
    date, and subtracts it from the target date. It then adds or subtracts
    the difference, gives the event object the new time, and then inserts
    it into Google Calendar.

    Each Google Calendar event object is cloned before it is sent off so
    there are no conflicts with already existing events.

    Parameters:
        service (googleapiclient.discovery.Resource): A Resource object that
            uses the Google Calendar v3 API
        events (list): a list of Google Calendar event objects
        dt (datetime.datetime): the date to upload the events to
    '''
    cal = service.events()
    events = clone_events(events)
    for event in events:
        start, end = get_start_and_end(event)
        diff = dt - start

        #Account for difference if start starts at midnight
        if start.hour == 0 and start.minute == 0 and start.second == 0:
            td = abs(datetime.timedelta(days=diff.days, seconds=time.timezone))
        else:
            td = abs(datetime.timedelta(days=diff.days+1, seconds=time.timezone))

        if dt_to_POSIX(end) > dt_to_POSIX(dt):
            newstart = start - td
            newend   = end   - td
        else:
            newstart = start + td
            newend   = end   + td

        event['start']['dateTime'] = RFC_from_UTC(newstart)
        event['end']['dateTime']   = RFC_from_UTC(newend)

        cal.insert(calendarId='primary', body=event).execute()

def load_events(filename):
    '''Loads events from a given filename

    filename MUST be from a .json format

    Parameters:
        filename (str): The filename of which to pull events from

    Returns:
        list: a list of Google Calendar event objects 
    '''
    with open(filename, 'r') as f:
        items = json.load(f)
        return items

def print_events(events):
    '''Takes a list of events and prints it to the console

    prints in the form: dateTime, summary

    If dateTime does not exist, it will print the date of an event. If summary
    does not exist, it will print "(No title)"

    Parameters:
        events (list): a list of Google Calendar event objects (or clones)
    '''
    start = None
    summary = None
    for event in events:
        try:
            start = event['start']['dateTime']
        except KeyError:
            start = event['start']['date']
        try:
            summary = event['summary']
        except KeyError:
            summary = '(No title)'
        print(start, summary)

def delete_events(service, events):
    '''Deletes a list of events from Google Calendar

    Parameters:
        service (googleapiclient.discovery.Resource): A Resource object that
            uses the Google Calendar v3 API
        events (list): a list of Google Calendar event objects
    '''
    cal = service.events()
    for event in events:
        cal.delete(calendarId='primary', eventId=event['id']).execute()

def dt_from_day(day):
    '''Returns a datetime.datetime object from a given string

    day can be of the following formats:
        today
        tomorrow
        yesterday
        relative date (see RELATIVE_DATE_PATTERN)
        YYYY-MM-DD    (see DATE_PATTERN)
        or from a day of the week (Monday, Tuesday, Wednesday, etc.)

    Parameters:
        day (str): a string representing a day

    Returns:
        datetime.datetime: a datetime object representing the given day
    '''
    if day == 'today':
        return datetime.datetime.today()
    elif day == 'tomorrow':
        return datetime.datetime.today() + datetime.timedelta(days=1)
    elif day == 'yesterday':
        return datetime.datetime.today() - datetime.timedelta(days=1)
    elif is_reldate(day):
        return dt_from_reldate(day)
    elif day in WEEKDAYS.keys():
        week = get_days_of_week(datetime.datetime.today()) 
        return week[WEEKDAYS[day]]
    elif re.match(DATE_PATTERN, day):
        return dt_from_date(day) 
    else:
        return None

def ask_for_confirmation(message):
    '''Asks for confirmation of something

    This function asks for the confirmation of something. A message
    is given to specify what to confirm. message will have a "[Y/N]"
    appended onto it.

    Valid answers are: yes, no, y, n (case is ignored)
    
    If a valid answer is not given, this will try again until a valid one
    is given.
    
    Parameters:
        message (str): a message specifying what to confirm
    Returns:
        bool: whether or not confirmation was given 
    '''
    answer = input(message + " [Y/N]")
    while answer.lower() not in ['y', 'yes', 'n', 'no']:
        answer = input('Please enter a valid answer.').lower()
    if answer == 'yes' or answer == 'y':
        return True
    else:
        return False

# End library

@click.group()
@click.pass_context
def cli(ctx):
    '''A command line tool for Google Calendar'''

    if os.path.isfile(FILE_DIRECTORY + '\\token.json'):
        store = file.Storage(FILE_DIRECTORY + '\\token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        try:
            service = build('calendar', 'v3', http=creds.authorize(Http()))
        except:
            print('Unable to connect to Google Calendar. Make sure you\'re connected to the internet.')
            sys.exit(1)

        ctx.obj = {}
        ctx.obj['service'] = service
    else:
        print('You haven\'t been authorized yet. Check github for more info.')
        return 0

@cli.command()
@click.argument('day', type=str)
@click.argument('filename', type=str)
@click.pass_context
def save(ctx, day, filename):
    '''Save a schedule of events to a file'''
    dt = dt_from_day(day)
    if not dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD.')
        return 1

    if not filename.endswith('.json'):
        filename += '.json'
    #Check if filename already exists in the current path and ask the user if
    #they wish to overwrite the current file
    exists = pathlib.Path(f'./{filename}').is_file()
    if exists:
        confirmed = ask_for_confirmation(f'{filename} already exists. Would you like to overwrite?')
        if confirmed:
            pass
        else:
            print('Save canceled.')
            return 2

    schedule_path = pathlib.Path(FILE_DIRECTORY + '/schedules')
    if not os.path.isdir(schedule_path):
        schedule_path.mkdir()

    events = get_events(ctx.obj['service'], dt)
    if not events:
        print('No events found. Save canceled.')
        return 3
    save_events(events, FILE_DIRECTORY + '\\schedules\\' + filename)
    print(f'Saved events from {day} to {filename}.')
    return 0

@cli.command()
@click.argument('filename', type=str)
@click.argument('day', type=str) 
@click.option('-u', 'until', type=str, help='if this is specified, then events from filename will be uploaded from day to the day specified by this option')
@click.option('-c', 'confirm', is_flag=True, help='asks to confirm before overwriting any events')
@click.pass_context
def upload(ctx, filename, day, until, confirm):
    '''Upload events from a file to a specific date'''
    dt = dt_from_day(day)
    if not dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD.')
        return 1

    if not filename.endswith('.json'):
        filename += '.json'
    if not os.path.exists(FILE_DIRECTORY + '\\schedules\\' + filename):
        print(f'{filename} does not exist.')
        return 4
    events = load_events(FILE_DIRECTORY + '\\schedules\\' + filename)
    if not events:
        print(f'No events found in {filename}.')
        return 3

    day_range = []
    if until:
        new_dt = dt_from_day(until)
        if not dt:
            print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD.')
            return 1

        if not dt < new_dt:
            print('Invalid date range. Please make sure your range is in order.')
            return 2

        for e in get_day_range(dt, new_dt):
            day_range.append(e)
    else:
        day_range.append(dt)
    
    for d in day_range:
        current_events = get_events(ctx.obj['service'], d)

        if current_events:
            if confirm:
                confirmed = ask_for_confirmation(f'There are already events registered for {date_from_dt(d)}, would you like to overwrite them?')
                if confirmed:
                    pass
                else:
                    continue
            delete_events(ctx.obj['service'], current_events)

        upload_events(ctx.obj['service'], events, d)

    if until:
        print(f'Uploaded events from {filename} to {day}.')
    else:
        print(f'Uploaded events from {filename} from {day} to {until}')
    return 0

@cli.command()
@click.option('-f', '--filename', is_flag=True, help='Specifies that the' 
        + ' name given is a filename')
@click.argument('name', type=str)
@click.pass_context
def list(ctx, name, filename):
    '''List events from a file or day'''
    if filename:
        if not name.endswith('.json'):
            name += '.json'
        exists = pathlib.Path(FILE_DIRECTORY + '\\schedules\\' + name).is_file()
        if exists:
            events = load_events(FILE_DIRECTORY + '\\schedules\\' + name) 
            if not events:
                print('No events found.')
                return 3
            print_events(events)
            return 0
        else:
            print('File does not exist.')
            return 1

    dt = dt_from_day(name)
    if not dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD.')
        return 1

    events = get_events(ctx.obj['service'], dt)
    if not events:
        print('No events found.')
        return 3
    print_events(events)
    return 0

@cli.command()
@click.argument('name', type=str)
@click.option('-f', 'isfile', is_flag=True, help='specifies that day is a filename')
@click.pass_context
def delete(ctx, name, isfile):
    '''Delete events from a specific day'''
    if isfile:
        if not name.endswith('.json'):
            name += '.json'
        if not os.path.exists(FILE_DIRECTORY + '\\schedules\\' + name):
            print(f'{name} does not exist.')
            return 4
        else:
            os.remove(FILE_DIRECTORY + '\\schedules\\' + name)
            print(f'{name} removed.')
            return 0

    dt = dt_from_day(name)
    if not dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD.')
        return 1
    events = get_events(ctx.obj['service'], dt)
    if not events:
        print('No events found. Deletion canceled.')
        return 3

    delete_events(ctx.obj['service'], events)
    print(f'Deleted events for {name}.')

@cli.command()
@click.argument('day', type=str)
@click.argument('newday', type=str)
@click.pass_context
def move(ctx, day, newday):
    '''Moves events from one day to another'''
    dt = dt_from_day(day)
    if not dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD.')
        return 1

    new_dt = dt_from_day(newday)
    if not new_dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD.')
        return 1

    current_events = get_events(ctx.obj['service'], new_dt)
    if current_events:
        confirmed = ask_for_confirmation(f'There are already events registered for {newday}, would you like to overwrite them?')
        if confirmed:
            delete_events(ctx.obj['service'], current_events)
        else:
            print('Move canceled.')
            return 0

    old_events = get_events(ctx.obj['service'], dt)
    new_events = clone_events(old_events)
    upload_events(ctx.obj['service'], new_events, new_dt)
    delete_events(ctx.obj['service'], old_events)

    print(f'Moved events from {day} to {newday}.')
    return 0

@cli.command()
@click.argument('day', type=str)
@click.argument('newday', type=str)
@click.option('-u', 'until', is_flag=True, help='specifies to copy over days until newday')
@click.option('-c', 'confirm', is_flag=True, help='asks to confirm before overwriting any events')
@click.pass_context
def copy(ctx, day, newday, until, confirm):
    '''Copies a schedule from a day to another day'''
    dt = dt_from_day(day)
    if not dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD.')
        return 1

    new_dt = dt_from_day(newday)
    if not new_dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD.')
        return 1

    raw_events = get_events(ctx.obj['service'], dt)
    if not raw_events:
        print('No events found for {day}. Copy canceled.')
        return 3

    events = clone_events(raw_events)

    day_range = []
    if until:
        if not dt < new_dt:
            print('Invalid date range. Please make sure your range is in order.')
            return 2

        for t in get_day_range(dt, new_dt):
            day_range.append(t)

        del day_range[0] #don't need first element
    else:
        day_range.append(new_dt)

    for d in day_range:
        current_events = get_events(ctx.obj['service'], d)

        if current_events:
            if confirm:
                confirmed = ask_for_confirmation(f'There are already events registered for {date_from_dt(d)}, would you like to overwrite them?')
                if confirmed:
                    pass
                else:
                    continue
            delete_events(current_events)

        upload_events(ctx.obj['service'], events, d)

    print(f'Copied events. from {date_from_dt(day)} to {date_from_dt(newday)}')
    return 0

@cli.command()
def list_schedules():
    '''Lists all of the schedules that are currently saved'''

    if os.path.isdir(FILE_DIRECTORY + '\\schedules'):
        files = os.listdir(FILE_DIRECTORY + '\\schedules')
        if files:
            for f in files:
                if f.endswith('.json'):
                    print(f)
            return 0
        print('No schedules found.')
        return 1
    print('No schedules found.')
    return 1

@cli.command()
def spawn():
    '''Spawns an Instance of Google Calendar in a web browser'''
    webbrowser.open('https://calendar.google.com/calendar', new=0, autoraise=True)

@cli.command()
@click.option('-ci', '--client_id', default=None, help='Your client ID')
@click.option('-cs', '--client_secret', default=None, help='Your client Secret')
def authorize(client_id, client_secret):
    '''Authorizes credentials for Google Api'''

    #workaround for oauth2 cuz the developers used argparse for some reason
    #first argument is deleted so argparse doesn't take "authorize" as an argument
    del sys.argv[0]

    tools.argparser.add_argument('-ci', '--client-id', type=str, required=True, help='The client ID of your GCP project')
    tools.argparser.add_argument('-cs', '--client-secret', type=str, required=True,
                             help='The client Secret of your GCP project')
    
    store = file.Storage(FILE_DIRECTORY + '\\token.json')
    creds = store.get()
    if not creds or creds.invalid:
        args = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
        flow = client.OAuth2WebServerFlow(args.client_id, args.client_secret, SCOPES)
        creds = tools.run_flow(flow, store, tools.argparser.parse_args())

    return 0

if __name__ == '__main__':
    cli()

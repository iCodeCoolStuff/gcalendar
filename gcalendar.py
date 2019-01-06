import calendar
import datetime
import json
import os
import pprint
import time
import re

import click

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

#Start library

DATE_PATTERN = re.compile(r'(\d{4})[:/.-](\d{1,2})[:/.-](\d{1,2})')
TIMESTAMP_PATTERN = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-]\d{2}:\d{2})')

WEEKDAYS = {
    'sunday':    0, 
    'monday':    1, 
    'tuesday':   2, 
    'wednesday': 3, 
    'thursday':  4, 
    'friday':    5, 
    'saturday':  6,
} 

def RFC_from_dt(date, time):
    return date + 'T' + time + 'Z'

def RFC_from_UTC(utc):
    return utc.isoformat() + 'Z'

def get_utc_offset():
    return time.localtime().tm_gmtoff / 3600

def get_min_today():
    today = datetime.datetime.today()
    return datetime.datetime(today.year, today.month, today.day, 0, 0, 0,)

def get_max_today():
    today = datetime.datetime.today()
    return datetime.datetime(today.year, today.month, today.day, 23, 59, 59)

def get_min_time(dt):
    return datetime.datetime(dt.year, dt.month, dt.day, 0, 0, 0,)

def get_max_time(dt):
    return datetime.datetime(dt.year, dt.month, dt.day, 23, 59, 59)

def dt_to_gmt(dt):
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
    date = re.search(TIMESTAMP_PATTERN, timestamp)
    return datetime.datetime(
            int(date.group(1)),
            int(date.group(2)),
            int(date.group(3)),
       hour=int(date.group(4)),
     minute=int(date.group(5)),
     second=int(date.group(6)))

def get_events(service, dt):
    mintime = RFC_from_UTC(dt_to_gmt(get_min_time(dt)))
    maxtime = RFC_from_UTC(dt_to_gmt(get_max_time(dt)))

    result = service.events().list(calendarId='primary', timeMin=mintime, timeMax=maxtime,
                                    singleEvents=True, orderBy='startTime').execute()
    items = result.get('items', [])
    if not items:
        return None
    return items

def dt_to_POSIX(dt):
    return calendar.timegm(dt.timetuple())

def get_start_and_end(event):
    s_timestamp = event['start']['dateTime']
    e_timestamp = event['end']['dateTime']

    start = utctimestamp_to_dt(s_timestamp)
    end   = utctimestamp_to_dt(e_timestamp)
    return (start, end)

def difference(dt1, dt2):
    year        = abs(dt1.year - dt2.year)
    month       = abs(dt1.month - dt2.month)
    day         = abs(dt1.day - dt2.day)
    hour        = abs(dt1.hour - dt2.hour)
    minute      = abs(dt1.minute - dt2.minute)
    second      = abs(dt1.second - dt2.second)
    microsecond = abs(dt1.microsecond - dt2.microsecond)

    return datetime.timedelta(year, month, day, hour, minute, second, microsecond)

def upload_events(service, events, dt):
    cal = service.events()
    for event in events:
        start, end = get_start_and_end(event)
        difference = difference(end, dt)

        if dt_to_POSIX(end) > dt_to_POSIX(dt):
            newstart = start - difference
            newend   = end   - difference
        else:
            newstart = start + difference
            newend   = end   + difference

        event['start']['dateTime'] = RFC_from_UTC(newstart)
        event['end']['dateTime']   = RFC_from_UTC(newend)
        print(event['start']['dateTime'])
        print(event['end']['dateTime'])

        event = cal.insert(calendarId='primary', body=event).execute()
        if event:
            print(event)

def get_days_of_week(dt):
    date = calendar.weekday(dt.year, dt.month, dt.day)
    if date == 6:
        days = []
        for i in range(6):
            days.append(datetime.datetime(dt.year, dt.month, dt.day+i))
        return days

    offset = 0
    while date != 6:
        offset -= 1 
        dt2 = dt + datetime.timedelta(days=offset)
        date = calendar.weekday(dt2.year, dt2.month, dt2.day)
    days = []
    for i in range(6):
        days.append(datetime.datetime(dt.year, dt.month, dt.day) + datetime.timedelta(days=(offset+i)))
    return days

def dt_from_date(date):
    dt = datetime.datetime(
            int(date.group(1)),
            int(date.group(2)), 
            int(date.group(3)))
    return dt

#Later maybe make it so that the events saved aren't completely barebones
def save_events(events, filename):
    new_events = []
    for event in events:
        new_event = {}
        new_event['summary'] = event['summary']
        new_event['start'] = {}
        new_event['end'] = {}

        new_event['start']['dateTime'] = event['start']['dateTime']
        new_event['end']['dateTime'] =  event['end']['dateTime']
        new_events.append(new_event)

    with open(filename + '.json', 'w') as f:
        print(new_events)
        json.dump(new_events, f)

def load_events(filename):
    with open(filename + '.json', 'r') as f:
        items = json.load(f)
        return items

def dt_from_day(day, week=None):
    if day = 'today':
        return datetime.datetime.today()
    elif day in WEEKDAYS.keys():
        if week == None:
            week = get_days_of_week(datetime.datetime.today()) 
        return week[WEEKDAYS[day]]
    elif re.search(DATE_PATTERN, day):
        return dt_from_date(day) 
    else:
        return None

def compare_weeks(week1, week2):
    newweek1 = _getcalweek(week1)
    newweek2 = _getcalweek(week2)    
    if newweek1 == newweek2:
        return True
    else:
        return False

#Helper function for the above function
def _getcalweek(week):
    newweek = []
    for day in week:
        newweek.append(calendar.weekday(day.year, day.month, day.day)) 
    return newweek

# End library

@click.group()
@click.pass_context
def cli(ctx):
    SCOPES = 'https://www.googleapis.com/auth/calendar'
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    ctx.obj = {}
    ctx.obj['service'] = service
    ctx.obj['week']    = get_days_of_week(datetime.datetime.today()) 

@cli.command()
@click.option('-d', '--day', type=str, default='today')
@click.argument('schedule_name', type=str)
@click.pass_context
def save(ctx, schedule_name, day):
    dt = dt_from_day(day)
    if not dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD')
        return 1

    #Check if schedule_name already exists in the current path and ask the user if
    #they wish to overwrite the current file
    if os.path.isdir(f'./{schedule_name}.json'):
        answer = input('{schedule_name}.json already exists. Would you like to overwrite? [Y/N]').lower()
        while answer.lower() in ['y', 'yes', 'n', 'no']:
            answer = input('Please enter a valid answer.').lower()
        if answer == 'yes' or answer == 'y':
            pass
        else:
            print('Aborted.')
            return 2

    events = get_events(ctx.obj['service'], dt)
    if not events:
        print('No events found. Save canceled.')
        return 3
    save_events(events, schedule_name)
    print(f'Saved {schedule_name} to {schedule_name}.json')
    return 0

@cli.command()
@click.argument('day', type=str) 
@click.argument('schedule_name', type=str)
@click.pass_context
def upload(ctx, schedule_name, day):
    dt = dt_from_day(day)
    if not dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD')
        return 1

    #Check if there are already events in the day time slot and ask the user if 
    #they wish to overwrite.
    cal_events = ctx.obj['service'].events().list()
    if cal_events:
        pass

    #Else just upload events 
    events = load_events(schedule_name)
    upload_events(ctx.obj['service'], events, dt) 
    print('Uploaded schedule')
    return 0

@cli.command()
@click.option('-f', '--isfilename', is_flag=True)
@click.argument('name', type=str)
@click.pass_context
def list(ctx, name, isfilename):
    if isfilename:
        exists = os.path.isdir('./{name}.json')
        if exists:
            events = load_events(name) 
        else:
            print('Schedule does not exist in the current directory.')

    dt = dt_from_day(name)
    if not dt:
        print('Invalid date. Must either be a day of the week or of the form YYYY-MM-DD')
        return 1

    events = get_events(ctx['service'], dt)
    if not events:
        print('No events found.')
        return 0
    for event in events:
        pprint.pprint(event)
    return 0

@cli.command()
@click.argument('date', type=str)
@pass_context
def switch(ctx, date):
    dt = dt_from_date(name)
    if not dt:
        print('Invalid date. Must be a of the form YYYY-MM-DD')
        return 1

    week = get_days_of_week(dt)
    if compare_weeks(week, ctx.obj['week']):
        print('Already at that week')
        return 2

    ctx.obj['week'] = week
    print('Switched to the week of {name}.')
    return 0

if __name__ == '__main__':
    cli()

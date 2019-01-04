import calendar
import datetime
import json
import pprint
import time
import re

import click

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

#Start library

DATE_PATTERN = re.compile(r'(\d{4}).(\d{2}).(\d{2})')

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
    today.hour        = 0
    today.second      = 0
    today.microsecond = 0
    return today 

def get_max_today():
    today = datetime.datetime.today()
    today.hour        = 23
    today.second      = 59
    today.microsecond = 59
    return today 

def get_min_time(dt):
    dt.hour        = 0
    dt.second      = 0
    dt.microsecond = 0
    return dt 

def get_max_time(dt):
    dt.hour        = 23
    dt.second      = 59
    dt.microsecond = 59
    return dt 

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

def get_events(service, dt):
    mintime = RFC_from_UTC(dt_to_gmt(dt))
    maxtime = RFC_from_UTC(dt_to_gmt(dt))

    result = service.events().list(calendarId='primary', timeMin=mintime, timeMax=maxtime,
                                    singleEvents=True, orderBy='startTime').execute()
    items = result.get('items', [])
    if not items:
        return None
    return items

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
        date -= 1
    days = []
    for i in range(6):
        days.append(datetime.datetime(dt.year, dt.month, dt.day+(i+offset)))
    return days

def dt_from_date(date):
    dt = datetime.datetime(
            date.group(1),
            date.group(2), 
            date.group(3))
    return dt

def save_events(events, filename):
    with open(filename + '.json', 'w') as f:
        json.dump(events, f)

def load_events(filename):
    with open(filename + '.json', 'r') as f:
        items = json.load(f)
        return items

# End library

@click.group()
@click.pass_context
def cli(ctx):
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    ctx.ensure_object(dict)
    ctx.obj['service'] = service
    ctx.obj['week']    = get_days_of_week(datetime.datetime.today()) 

@cli.command()
@click.option('--day', type=str, default='today')
@click.argument('schedule_name', type=str)
@click.pass_context
def save(ctx, schedule_name, day):
    if day == 'today':
        events = get_events(ctx.obj, datetime.datetime.today())
    elif day in WEEKDAYS.keys():
        events = get_events(ctx.obj, ctx.obj['week'][WEEKDAYS[day]])
    elif re.search(DATE_PATTERN, day):
        date = re.search(DATE_PATTERN, day)
        events = get_events(ctx.obj, dt_from_date(date))
    else:
        print('something went wrong with the date')
        return 1

    save_events(events, schedule)
    print(f'Saved {schedule_name} to {schedule_name}.json')
    return 0

if __name__ == '__main__':
    cli()

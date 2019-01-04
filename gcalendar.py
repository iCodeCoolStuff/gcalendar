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

DATE_PATTERN = re.compile(r'(\d{4}).(\d{2}).(\d{2})')

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

def get_events(service):
    today = datetime.datetime.today() 

    mintime = RFC_from_UTC(dt_to_gmt(get_min_today()))
    maxtime = RFC_from_UTC(dt_to_gmt(get_max_today()))

    result = service.events().list(calendarId='primary', timeMin=mintime, timeMax=maxtime,
                                    singleEvents=True, orderBy='startTime').execute()
    items = result.get('items', [])
    if not items:
        return None
    return items

def get_days_of_week():


def save_events(events, filename):
    with open(filename, 'w') as f:
        json.dump(events, f)

def load_events(filename):
    with open(filename, 'r') as f:
        items = json.load(f)
        return items

@click.group()
@click.pass_context
def cli(ctx):
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    ctx.obj = service

@cli.command()
@click.option('--day', type=str, default='today')
@click.argument('schedule_name', type=str)
@click.pass_context
def save(ctx, schedule_name, day):
    events = get_current_events(ctx.obj)
    

if __name__ == '__main__':
    cli()

import datetime
import json
import pathlib
import pprint
import re
import time

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

date_pattern = re.compile('(\d{4})-(\d{2})-(\d{2})')

def RFC_from_dt(date, time):
    return date + 'T' + time + 'Z'

def RFC_from_UTC(utc):
    return utc.isoformat() + 'Z'

def get_current_date():
    date = re.search(date_pattern, str(datetime.datetime.today()))
    return date.group(0)

def get_utc_offset():
    return time.localtime().tm_gmtoff / 3600

def get_min_today():
    today = datetime.datetime.today()
    return datetime.datetime(today.year, today.month, today.day, 0, 0, 0) 

def get_max_today():
    today = datetime.datetime.today()
    return datetime.datetime(today.year, today.month, today.day, 23, 59, 59)

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

def get_current_events(service):
    mintime = RFC_from_UTC(dt_to_gmt(get_min_today()))
    maxtime = RFC_from_UTC(dt_to_gmt(get_max_today()))

    result = service.events().list(calendarId='primary', timeMin=mintime, timeMax=maxtime,
                                    singleEvents=True, orderBy='startTime').execute()
    items = result.get('items', [])
    if not items:
        return None
    return items

def save(events, filename):
    with open(filename, 'w') as f:
        json.dump(events, f)

def load(filename):
    with open(filename, 'r') as f:
        items = json.load(f)
        return items

def main():
    """
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    events = get_current_events(service)
    """

    """
    print('Getting today\'s calendar events')
    events = get_current_events(service)
    if events is None:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])
    """
    
    items = load('data.json')
    print(items)

if __name__ == '__main__':
    main()

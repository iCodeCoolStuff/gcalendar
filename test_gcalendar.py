import calendar
import datetime
import pprint
import unittest
import re
import time

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

import gcalendar

class TestTimeFunctions(unittest.TestCase):

    def test_RFC_from_UTC(self):
        dt = datetime.datetime(2019, 9, 8)
        self.assertEqual(gcalendar.RFC_from_UTC(dt), '2019-09-08T00:00:00Z')

    def test_get_utc_offset(self):
        self.assertEqual(gcalendar.get_utc_offset(), -5)

    def test_get_min_time(self):
        dt = datetime.datetime(2019, 10, 31)
        self.assertEqual(gcalendar.get_min_time(dt), datetime.datetime(2019, 10, 31, 0, 0, 0))

    def test_get_max_time(self):
        dt = datetime.datetime(2019, 7, 16)
        self.assertEqual(gcalendar.get_max_time(dt), datetime.datetime(2019, 7, 16, 23, 59, 59))

    def test_gmt(self):
        now = datetime.datetime.now()
        nowtd = datetime.timedelta(hours=5)
        self.assertEqual(gcalendar.gmt(now), now - nowtd)

    def test_dt_to_POSIX(self):
        dt = datetime.datetime.now() 
        self.assertEqual(gcalendar.dt_to_POSIX(dt), calendar.timegm(dt.timetuple()))

    def test_get_min_and_max(self):
        dt = datetime.datetime(2019, 12, 29)
        dtmax = datetime.datetime(2019, 12, 29, 23, 59, 59)
        self.assertEqual(gcalendar.get_min_and_max(dt), (dt, dtmax))

    def test_get_days_of_week(self):
        week = [
            datetime.datetime(2019, 11, 10),
            datetime.datetime(2019, 11, 11),
            datetime.datetime(2019, 11, 12),
            datetime.datetime(2019, 11, 13),
            datetime.datetime(2019, 11, 14),
            datetime.datetime(2019, 11, 15),
            datetime.datetime(2019, 11, 16),
        ]
        for i in range(len(week)):
            self.assertEqual(gcalendar.get_days_of_week(week[i]), week)
    
    def test_get_current_week(self):
        today = datetime.datetime.now()
        week = gcalendar.get_current_week()
        self.assertEqual(week, gcalendar.get_days_of_week(today))

    def test_get_day_range(self):
        dt1 = gcalendar.dt_from_day('sunday')
        dt2 = gcalendar.dt_from_day('saturday')

        self.assertEqual(gcalendar.get_day_range(dt1, dt2), gcalendar.get_current_week())

class TestEventFunctions(unittest.TestCase):

    def setUp(self):
        #build service if doesn't already exist
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', 'https://www.googleapis.com/auth/calendar')
            creds = tools.run_flow(flow, store)
        self.service = build('calendar', 'v3', http=creds.authorize(Http()))

        #new events for a random date
        self.dt = datetime.datetime(2020, 1, 2)
        self.events = gcalendar.get_events(self.service, self.dt)

    def tearDown(self):
        #replace events
        #gcalendar.upload_events(self.service, self.events, self.dt)
        pass

    
    def test_get_start_and_end(self):
        for event in self.events:
            start = event['start']['dateTime']
            end = event['end']['dateTime']  
            
            dstart, dend = gcalendar.get_start_and_end(event)
            #utc offset
            self.assertEqual((dstart.isoformat()+'-05:00', dend.isoformat()+'-05:00'), (start, end))

    
    def test_save_events(self):
        newevents = []
        for event in self.events:
            newevent = gcalendar.clone_event(event)
            newevents.append(newevent)
        
        gcalendar.save_events(newevents, 'test_events.json')
        levents = gcalendar.load_events('test_events.json')
        self.assertEqual(newevents, levents)
    
    

    def test_load_events(self):
        gcalendar.save_events(self.events, 'test_events.json')
        self.events = gcalendar.load_events('test_events.json')

    def test_print_events(self):
        gcalendar.print_events(self.events)

    
    '''
    def test_delete_events(self):
        events = gcalendar.get_events(self.service, self.dt)
        gcalendar.delete_events(self.service, events)
        self.assertEqual(gcalendar.get_events(self.service, self.dt), None)
    
    '''
    

class TestRegexFunctions(unittest.TestCase):

    def setUp(self):
        self.date_pattern = re.compile(r'(\d{4})[:/.-](\d{1,2})[:/.-](\d{1,2})')
        self.timestamp_pattern = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-]\d{2}:\d{2})?')
        self.relative_date_pattern = re.compile('(last|next)\s*(\w+)\s*', re.IGNORECASE)

    def tearDown(self):
        pass

    def test_dt_from_day(self):
        self.assertEqual(gcalendar.dt_from_day('today'), datetime.datetime.today())

    def test_utctimestamp_to_dt(self):
        now = datetime.datetime(2019, 3, 8, 4, 4, 45)
        self.assertEqual(now, gcalendar.utctimestamp_to_dt('2019-03-08T04:04:45'))

    def test_date_from_dt(self):
        now = datetime.datetime.now() 
        self.assertEqual(gcalendar.date_from_dt(now), f'{now.year}-{now.month}-{now.day}')

    def test_dt_from_date(self):
        dt = datetime.datetime(2019, 3, 8)
        self.assertEqual(gcalendar.dt_from_date('2019-3-8'), dt)

    def test_is_reldate(self):
        stuff = ['next monday',
        'next tuesday',
        'next wednesday',
        'next thursday',
        'next friday',
        'next saturday',
        'next sunday']

        for s in stuff:
            self.assertEqual(True, gcalendar.is_reldate(s))

if __name__ == '__main__':
    unittest.main()

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
        dt = datetime.datetime(2019, 6, 15, now.hour, now.minute, now.second, now.microsecond)  
        self.assertEqual(gcalendar.gmt(dt), dt + nowtd)

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

class TestEventFunctions(unittest.TestCase):

    def setUp(self):
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        self.service = build('calendar', 'v3', http=creds.authorize(Http()))

    def tearDown(self):
        pass


    def test_get_start_and_end(self):
        today = datetime.datetime.today()
        events = gcalendar.get_events(self.service, today) 
        for event in events:
            start = event['start']['dateTime']
            end = event['end']['dateTime']  
            
            dstart, dend = gcalendar.get_start_and_end(event)
            #utc offset
            self.assertEqual((dstart.isoformat()+'-05:00', dend.isoformat()+'-05:00'), (start, end))

    def test_clone_event(self):
        #Doesn't need testing
        pass

    def test_save_events(self):
        events = gcalendar.get_events(self.service, datetime.datetime.today())
        newevents = []
        for event in events:
            newevent = gcalendar.clone_event(event)
            newevents.append(newevent)
        
        gcalendar.save_events(newevents, 'test_events.json')
        levents = gcalendar.load_events('test_events.json')
        self.assertEqual(newevents, levents)

    def test_load_events(self):
        events = gcalendar.get_events(self.service, datetime.datetime.today())
        gcalendar.save_events(events, 'test_events.json')
        events = gcalendar.load_events('test_events.json')

    def test_print_events(self):
        events = gcalendar.get_events(self.service, datetime.datetime.today())
        gcalendar.print_events(events)

    def test_delete_events(self):
        #upload
        events = gcalendar.get_events(self.service, datetime.datetime.today())
        new_events = []
        for event in events:
            new_events.append(gcalendar.clone_event(event))
        gcalendar.upload_events(self.service, new_events, datetime.datetime(2019, 3, 3))
        #delete 
        events2 = gcalendar.get_events(self.service, datetime.datetime(2019, 3, 3,))
        gcalendar.delete_events(self.service, events2)
    

class TestRegexFunctions(unittest.TestCase):

    def setUp(self):
        self.date_pattern = re.compile(r'(\d{4})[:/.-](\d{1,2})[:/.-](\d{1,2})')
        self.timestamp_pattern = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-]\d{2}:\d{2})?')
        self.relative_date_pattern = re.compile('(last|next)\s*(\w+)\s*', re.IGNORECASE)

    def tearDown(self):
        pass

    def test_ask_for_confirmation(self):
        #Doesn't need testing
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
        stuff = ['last monday',
        'last tuesday',
        'last wednesday',
        'last thursday',
        'last friday',
        'last saturday',
        'last sunday']

        for s in stuff:
            self.assertEqual(True, gcalendar.is_reldate(s))

    def test_dt_from_reldate(self):
        next_saturday = gcalendar.dt_from_date('2019-1-19')
        self.assertEqual(next_saturday, gcalendar.dt_from_reldate('next saturday'))

if __name__ == '__main__':
    unittest.main()

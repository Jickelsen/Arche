# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase
from datetime import datetime
from datetime import timedelta
from calendar import timegm

from pyramid import testing
from pyramid.i18n import get_localizer
from pyramid.response import Response


def _dummy_view(*args):
    return {}


class GetViewTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.utils import get_view
        return get_view

    def _fixture(self, name = ''):
        self.config.add_view(_dummy_view, context=testing.DummyResource, name = name)

    def test_no_view(self):
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.assertEqual(self._fut(context, request), None)

    def test_default_view(self):
        self._fixture()
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.failUnless(self._fut(context, request))

    def test_named_view(self):
        self._fixture(name = 'hello')
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.failUnless(self._fut(context, request, view_name = 'hello'))


class DateTimeHandlerTests(TestCase):
    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.utils import DateTimeHandler
        return DateTimeHandler

    def test_date_format(self):
        obj = self._cut()
        date = obj.timezone.localize(datetime.strptime('1999-12-13', "%Y-%m-%d"))
        self.assertEqual(obj.format_dt(date, parts = 'd'), u'12/13/99')

    def test_time_format(self):
        obj = self._cut()
        date_and_time = obj.timezone.localize(datetime.strptime('1999-12-14 19:12', "%Y-%m-%d %H:%M"))
        self.assertEqual(obj.format_dt(date_and_time, parts = 't'), u'7:12 PM')

    def test_datetime_format(self):
        obj = self._cut()
        date_and_time = obj.timezone.localize(datetime.strptime('1999-12-14 19:12', "%Y-%m-%d %H:%M"))
        self.assertEqual(obj.format_dt(date_and_time), '12/14/99, 7:12 PM')
    
    def test_datetime_sv_locale(self):
        obj = self._cut(locale = 'sv')
        date_and_time = obj.timezone.localize(datetime.strptime('1999-12-14 19:12', "%Y-%m-%d %H:%M"))
        self.assertEqual(obj.format_dt(date_and_time), '1999-12-14 19:12')

    def test_datetime_full_sv(self):
        obj = self._cut(locale = 'sv', tz_name = 'Europe/Stockholm')
        date_and_time = obj.timezone.localize(datetime.strptime('1999-12-14 19:12', "%Y-%m-%d %H:%M"))
        self.assertEqual(obj.format_dt(date_and_time, format='full'), u'tisdagen den 14:e december 1999 kl. 19:12:00 Centraleuropa, normaltid')

    def test_tz_to_utc(self):
        obj = self._cut(tz_name = "Europe/Stockholm")
        fmt = '%Y-%m-%d %H:%M %Z%z'
        date_time = datetime.strptime('1999-12-14 19:12', "%Y-%m-%d %H:%M")
        localized_dt = obj.timezone.localize(date_time)
        utc_dt = obj.tz_to_utc(localized_dt)
        result = utc_dt.strftime(fmt)
        self.assertEquals(result, '1999-12-14 18:12 UTC+0000')

    def test_localnow(self):
        obj = self._cut()
        now = obj.localnow()
        # we don't check for exactly equal timezones due to DST changes
        self.assertEquals(str(now.tzinfo), str(obj.timezone))

    def test_dst_timedelta(self):
        """Check that timedeltas take DST into account.
        """
        obj = self._cut(tz_name = "Europe/Stockholm")
        date_time1 = datetime.strptime('1999-12-14 18:12', "%Y-%m-%d %H:%M")
        date_time2 = datetime.strptime('1999-08-14 18:12', "%Y-%m-%d %H:%M")
        l_dt1 = obj.timezone.localize(date_time1)
        l_dt2 = obj.timezone.localize(date_time2)
        self.assertNotEqual(l_dt1 - l_dt2, timedelta(days=122))
        self.assertEquals(l_dt1 - l_dt2, timedelta(days=122, hours=1))

    def test_format_relative(self):
        request = testing.DummyRequest()
        locale = get_localizer(request)
        trans = locale.translate
        obj = self._cut()
        now = obj.utcnow()
        fut = obj.format_relative
        #Just now
        self.assertEqual(fut(now), u"Just now")

        #30 seconds ago - is this really a smart test? :)
        now = obj.utcnow()
        out = fut(now - timedelta(seconds=30))
        self.assertEqual(trans(out), u"30 seconds ago")

        #90 seconds ago - I.e. after 1 minute
        out = fut(now - timedelta(seconds=90))
        self.assertEqual(trans(out), u"1 minute ago")

        #5 minutes ago
        out = fut(now - timedelta(minutes=5))
        self.assertEqual(trans(out), u"5 minutes ago")

        #1 hour ago
        out = fut(now - timedelta(hours=1, seconds=1))
        self.assertEqual(trans(out), u"1 hour ago")

        #5 hours ago
        out = fut(now - timedelta(hours=6, seconds=1))
        self.assertEqual(trans(out), u"6 hours ago")
        
        #After about 1 day, return regular date time format
        date = obj.timezone.localize( datetime.strptime('1999-08-14 18:12', "%Y-%m-%d %H:%M") )
        self.assertEqual(fut(date), u'8/14/99, 6:12 PM')

    def test_format_relative_from_timestamp(self):
        request = testing.DummyRequest()
        locale = get_localizer(request)
        trans = locale.translate
        obj = self._cut()
        time = obj.utcnow() - timedelta(minutes=5)
        timestamp = timegm(time.timetuple())
        out = obj.format_relative(timestamp)
        self.assertEqual(trans(out), u"5 minutes ago")

    def test_relative_time_format_no_tz_set(self):
        obj = self._cut()
        self.assertRaises(ValueError, obj.format_relative, datetime.now())

    def test_relative_time_format_future(self):
        obj = self._cut()
        time = obj.utcnow() + timedelta(minutes = 10)
        out = obj.format_relative(time)
        self.assertEqual(out, obj.format_dt(time))


class GenerateSlugTests(TestCase):

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.utils import generate_slug
        return generate_slug

    def test_chineese(self):
        context = testing.DummyResource()
        hello = "您好"
        self.assertEqual(self._fut(context, hello), "nin-hao")

    def test_ukranian(self):
        context = testing.DummyResource()
        hello = "Привіт"
        self.assertEqual(self._fut(context, hello), "privit")

    def test_swedish(self):
        context = testing.DummyResource()
        text = "Héj åäö"
        self.assertEqual(self._fut(context, text), "hej-aao")

    def test_registered_views(self):
        self.config.add_view(_dummy_view, name = 'dummy', context = testing.DummyResource)
        context = testing.DummyResource()
        self.assertEqual(self._fut(context, 'dummy'), "dummy-1")

    def test_with_existing_keys(self):
        context = testing.DummyResource()
        context['hello'] = testing.DummyResource()
        self.assertEqual(self._fut(context, 'hello'), "hello-1")


class MIMETypeViewsTests(TestCase):

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.utils import MIMETypeViews
        return MIMETypeViews
    
    def test_get_mimetype(self):
        obj = self._cut()
        obj['video/mp4'] = 'hello'
        self.assertEqual(obj['video/mp4'], 'hello') 
        
    def test_get_with_generic_type(self):
        obj = self._cut()
        obj['video/*'] = 'hello'
        self.assertEqual(obj['video/mp4'], 'hello')
        
    def test_contains_with_generic(self):
        obj = self._cut()
        obj['video/*'] = 'hello'
        self.assertIn('video/hello', obj)
        
    def test_get_with_generic(self):
        obj = self._cut()
        obj['video/mp4'] = 'hello'
        self.assertEqual(obj.get('video/mp4'), 'hello')
        self.assertEqual(obj.get('video/something'), None)
        obj['video/*'] = 'world'
        self.assertEqual(obj.get('video/mp4'), 'hello')
        self.assertEqual(obj.get('video/something'), 'world')
        self.assertEqual(obj.get('video/*'), 'world')
        
    def test_get_mimetype_views(self):
        self.config.include('arche.utils')
        from arche.utils import get_mimetype_views
        self.assertIsInstance(get_mimetype_views(), self._cut)
        
    def test_integration(self):
        self.config.include('arche.utils')
        from arche.views.file import mimetype_view_selector
        self.config.add_mimetype_view('test/*', 'helloworld')
        
        class DummyContext(testing.DummyResource):
            mimetype = 'test/boo'
            
        L = []
        def dummy_view(*args):
            L.append(args)
            return ''
            
        self.config.add_view(dummy_view, context=DummyContext, name='helloworld', renderer='string')
        context = DummyContext()
        request = testing.DummyRequest()
        result = mimetype_view_selector(context, request)
        self.assertEqual(len(L), 1)
        self.assertIsInstance(result, Response)

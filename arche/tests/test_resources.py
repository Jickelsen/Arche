from unittest import TestCase

from pyramid import testing
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from arche.interfaces import IBase
from arche.interfaces import IToken


class BaseTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.resources import Base
        return Base

    def test_verify_class(self):
        verifyClass(IBase, self._cut)

    def test_verify_object(self):
        verifyObject(IBase, self._cut())


class TokenTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.resources import Token
        return Token

    def test_verify_class(self):
        verifyClass(IToken, self._cut)

    def test_verify_object(self):
        verifyObject(IToken, self._cut())

    def test_eq(self):
        obj1 = self._cut()
        obj2 = self._cut()
        self.assertNotEqual(obj1, obj2)
        obj2.token = obj1.token = '1'
        self.assertEqual(obj1, obj2)

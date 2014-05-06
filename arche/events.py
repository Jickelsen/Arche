from zope.interface import implementer
from repoze.folder.events import (ObjectAddedEvent,
                                  ObjectWillBeRemovedEvent) #API

from arche.interfaces import (IObjectUpdatedEvent,
                              IViewInitializedEvent)


@implementer(IObjectUpdatedEvent)
class ObjectUpdatedEvent(object):
    """ When an object has been updated in some way.
    """
    object = None
    changed = frozenset()
    
    def __init__(self, _object, changed = ()):
        self.object = _object
        self.changed = set(changed)


@implementer(IViewInitializedEvent)
class ViewInitializedEvent(object):
    """ When a base content view has been initalized. It will not be used for views
        like thumbnail or download, where there's no reason to inject things at this point. """

    def __init__(self, _object):
        self.object = _object

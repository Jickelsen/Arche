from UserDict import IterableUserDict

from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from pyramid.security import (NO_PERMISSION_REQUIRED,
                              Everyone,
                              Authenticated,
                              Allow,
                              Deny,
                              ALL_PERMISSIONS,
                              DENY_ALL,
                              authenticated_userid)
from pyramid.decorator import reify
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_root
from zope.component import adapter
from zope.interface import implementer
from zope.component import ComponentLookupError

from arche import _
from arche.interfaces import IBase
from arche.interfaces import IRoot
from arche.interfaces import IRoles
from arche.interfaces import IGroups


ROLE_ADMIN = 'role:Administrator'
ROLE_EDITOR = 'role:Editor'
ROLE_VIEWER = 'role:Viewer'
ROLE_OWNER = 'role:Owner'

PERM_VIEW = 'perm:View'
PERM_EDIT = 'perm:Edit'
PERM_REGISTER = 'perm:Register'
PERM_DELETE = 'perm:Delete'


def non_inherited_roles(request = None):
    #FIXME: Add to regostry instead
    return set([ROLE_OWNER])

def groupfinder(name, request):
    result = set()
    if name:
        groups = get_groups(request.context, request.registry)
        result.update(groups.groups_for_userid(name))
        non_inherited = non_inherited_roles(request)
        context = request.context
        while context:
            try:
                result.update([x for x in context.roles.get(name, ()) if x not in non_inherited])
            except AttributeError:
                pass
            context = context.__parent__
    return result

def get_available_roles(registry = None):
    """ Get roles registry. """
    if registry is None:
        registry = get_current_registry()
    return registry.available_roles


@adapter(IBase)
@implementer(IRoles)
class Roles(IterableUserDict):

    def __init__(self, context):
        self.context = context
        try:
            self.data = self.context.__local_roles__
        except AttributeError:
            self.context.__local_roles__ = OOBTree()
            self.data = self.context.__local_roles__

    def __setitem__(self, key, value):
        if value:
            #Make sure it exist
            roles = get_available_roles()
            [roles[k] for k in value]
            self.data[key] = OOSet(value)
        else:
            del self.data[key]

    def set_from_appstruct(self, value):
        marker = object()
        formatted_roles = dict([(x['principal'], x['roles']) for x in value])
        print formatted_roles
        removed_principals = set()
        [removed_principals.add(x) for x in self if x not in formatted_roles]
        [self.pop(x) for x in removed_principals]
        for (k, v) in formatted_roles.items():
            if self.get(k, marker) != v:
                self[k] = v

    def get_appstruct(self):
        return [{'principal': k, 'roles': v} for (k, v) in self.items()]


@adapter(IRoot)
@implementer(IGroups)
class Groups(IterableUserDict):
    #FIXME: Probably needs an update and group objects?
    #Lookup userid to group?
    #FIXME: Not active yet!

    def __init__(self, context):
        self.context = context
        try:
            self.data = self.context.__groups__
        except AttributeError:
            self.context.__groups__ = OOBTree()
            self.data = self.context.__groups__

    def __setitem__(self, key, value):
        assert key.startswith('groups.')
        self.data[key] = OOSet(value)

    def groups_for_userid(self, userid):
        #FIXME
        return ()
        for (name, members) in self.items():
            if userid in members:
                pass
                #yield name

def get_groups(context, registry = None):
    root = find_root(context)
    if registry is None:
        registry = get_current_registry()
    try:
        return registry.getAdapter(root, IGroups)
    except ComponentLookupError:
        return Groups(root)

def get_local_roles(context, registry = None):
    if registry is None:
        registry = get_current_registry()
    try:
        return registry.getAdapter(context, IRoles)
    except ComponentLookupError:
        #FIXME: Does this mean that roles shouldn't be stored here...?
        return Roles(context)

#FIXME
BASE_ACL = [(Allow, ROLE_ADMIN, ALL_PERMISSIONS),
            DENY_ALL]


def get_default_acl(registry = None):
    if registry is None:
        registry = get_current_registry()
    return BASE_ACL


def includeme(config):
    config.registry.available_roles = roles = {}
    roles[ROLE_ADMIN] = _(u"Administrator")
    roles[ROLE_EDITOR] = _(u"Editor")
    roles[ROLE_VIEWER] = _(u"Viewer")
    roles[ROLE_OWNER] = _(u"Owner")
    config.registry.registerAdapter(Groups)
    config.registry.registerAdapter(Roles)

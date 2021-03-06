from UserDict import IterableUserDict
from datetime import datetime
from hashlib import sha512
from uuid import uuid4
import inspect

from BTrees.OOBTree import OOBTree
from PIL.Image import core as pilcore
from ZODB.blob import Blob
from babel.dates import format_date
from babel.dates import format_datetime
from babel.dates import format_time
from html2text import HTML2Text
from persistent import Persistent
from plone.scale.scale import scaleImage
from pyramid.compat import map_
from pyramid.i18n import TranslationString
from pyramid.interfaces import IRequest
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier
from pyramid.renderers import render
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from repoze.lru import LRUCache
from slugify import UniqueSlugify
from zope.component import adapter
from zope.interface import implementer
from zope.interface import providedBy
from zope.interface.interfaces import ComponentLookupError
import pytz
import six

from arche import _
from arche.interfaces import (IBase,
                              IFileUploadTempStore,
                              IBlobs,
                              IFlashMessages,
                              IFolder,
                              IJSONData,
                              IThumbnails,
                              IThumbnailedContent,
                              IRoot,
                              IRegistrationTokens,
                              IDateTimeHandler,
                              IObjectUpdatedEvent,
                              IContentView)
from deform.widget import filedict


def add_content_factory(config, ctype, addable_to = (), addable_in = ()):
    """ Add a class as a content factory. It will be addable through the add menu
        for anyone with the correct add permission, in a context where it's marked
        as addable. You may set an addable context here as well.
        
        Example:
            config.add_content_factory(MyClass, addable_to = ('Root', 'Document',), addable_in = 'Image')
    """
    assert inspect.isclass(ctype)
    factories = get_content_factories(config.registry)
    factories[ctype.type_name] = ctype
    if addable_to:
        config.add_addable_content(ctype.type_name, addable_to)
    if addable_in:
        if isinstance(addable_in, six.string_types):
            addable_in = (addable_in,)
        for ctype_name in addable_in:
            config.add_addable_content(ctype_name, ctype.type_name)

def get_content_factories(registry = None):
    if registry is None:
        registry = get_current_registry()
    try:
        return registry._content_factories
    except AttributeError:
        raise Exception("Content factories registry not initialized, include arche.utils")


def add_addable_content(config, ctype, addable_to):
    addable = config.registry._addable_content.setdefault(ctype, set())
    if isinstance(addable_to, six.string_types):
        addable.add(addable_to)
    else:
        addable.update(addable_to)

def get_addable_content(registry = None):
    if registry is None:
        registry = get_current_registry()
    try:
        return registry._addable_content
    except AttributeError:
        raise Exception("Addable content registry not initialized, include arche.utils")

def add_content_schema(config, type_name, schema, name):
    assert inspect.isclass(schema)
    if inspect.isclass(type_name):
        type_name = type_name.__name__
    schemas = get_content_schemas(config.registry)
    ctype_schemas = schemas.setdefault(type_name, {})
    ctype_schemas[name] = schema

def get_content_schemas(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry._content_schemas

def add_content_view(config, type_name, name, view_cls):
    """ Register a view as selectable for a content type.
        view_cls must implement IContentView.
    """
    assert IContentView.implementedBy(view_cls), "view_cls argument must be a class that implements arche.interfaces.IContentView"
    if not name:
        raise ValueError("Name must be specified and can't be an empty string. Specify 'view' to override the default view.")
    if inspect.isclass(type_name):
        type_name = type_name.type_name
    content_factories = get_content_factories(config.registry)
    if type_name not in content_factories:
        raise KeyError('No content type with name %s' % type_name)
    views = get_content_views(config.registry)
    ctype_views = views.setdefault(type_name, {})
    ctype_views[name] = view_cls

def get_content_views(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry._content_views

def generate_slug(parent, text, limit=40):
    """ Suggest a name for content that will be added.
        text is a title or similar to be used.
    """
    #Stop words configurable?
    #We don't have any language settings anywhere
    #Note about kw uids: It's keys already used.
    used_names = set(parent.keys())
    request = get_current_request()
    used_names.update(get_context_view_names(parent, request))
    sluggo = UniqueSlugify(to_lower = True,
                           stop_words = ['a', 'an', 'the'],
                           max_length = 80,
                           uids = used_names)
    suggestion = sluggo(text)
    if not len(suggestion):
        raise ValueError("When text was made URL-friendly, nothing remained.")
    if check_unique_name(parent, request, suggestion):
        return suggestion
    raise KeyError("No unique id could be found")

def get_context_view_names(context, request):
    provides = [IViewClassifier] + map_(
        providedBy,
        (request, context)
    )
    return [x for (x, y) in request.registry.adapters.lookupAll(provides, IView)]

def check_unique_name(context, request, name):
    """ Check if there's an object with the same name or a registered view with the same name.
        If there is, return False.
    """
    if name in context:
        return False
    if get_view(context, request, view_name = name) is None:
        return True
    return False

def get_view(context, request, view_name = ''):
    """ Returns view callable if a view is registered.
    """
    provides = [IViewClassifier] + map_(
        providedBy,
        (request, context)
    )
    return request.registry.adapters.lookup(provides, IView, name=view_name)


@adapter(IRequest)
@implementer(IFlashMessages)
class FlashMessages(object):
    """ See IFlashMessages"""

    def __init__(self, request):
        self.request = request

    def add(self, msg, type='info', dismissable = True, auto_destruct = True):
        css_classes = ['alert']
        css_classes.append('alert-%s' % type)
        if dismissable:
            css_classes.append('alert-dismissable')
        css_classes = " ".join(css_classes)
        flash = {'msg':msg, 'dismissable': dismissable, 'css_classes': css_classes, 'auto_destruct': auto_destruct}
        self.request.session.flash(flash)

    def get_messages(self):
        for message in self.request.session.pop_flash():
            message['id'] = unicode(uuid4())
            yield message

    def render(self):
        response = {'get_messages': self.get_messages}
        return render("arche:templates/flash_messages.pt", response, request = self.request)

def get_flash_messages(request):
    try:
        return request.registry.getAdapter(request, IFlashMessages)
    except ComponentLookupError:
        return FlashMessages(request)

def hash_method(value, registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.settings['arche.hash_method'](value)

def default_hash_method(value):
    return sha512(value).hexdigest()

def upload_stream(stream, _file):
    size = 0
    while 1:
        data = stream.read(1<<21)
        if not data:
            break
        size += len(data)
        _file.write(data)
    return size


@adapter(IRequest)
@implementer(IFileUploadTempStore)
class FileUploadTempStore(object):
    """
    A temporary storage for file file uploads

    File uploads are stored in the session so that you don't need
    to upload your file again if validation of another schema node
    fails.
    """

    def __init__(self, request):
        self.request = request

    @property
    def storage(self):
        return self.request.session.setdefault('upload_tmp', {})

    def keys(self):
        return [k for k in self.storage.keys() if not k.startswith('_')]

    def get(self, key, default = None):
        return key in self.keys() and self.storage[key] or default

    def clear(self):
        self.request.session.pop('upload_tmp')

    def __setitem__(self, name, value):
        value = value.copy()
        fp = value.pop('fp')
        value['file_contents'] = fp.read()
        fp.seek(0)
        self.storage[name] = value

    def __getitem__(self, name):
        value = self.storage[name].copy()
        value['fp'] = six.StringIO(value.get('file_contents'))
        return value

    def __delitem__(self, name):
        del self.storage[name]

    def __contains__(self, name):
        return name in self.storage

    def preview_url(self, name):
        #To make deform happy
        return None


@implementer(IBlobs)
@adapter(IBase)
class Blobs(IterableUserDict):
    """ Adapter that handles blobs in context
    """
    def __init__(self, context):
        self.context = context
        self.data = getattr(context, '__blobs__', {})

    def __setitem__(self, key, item):
        if not isinstance(item, BlobFile):
            raise ValueError("Only instances of BlobFile allowed.")
        if not isinstance(self.data, OOBTree):
            self.data = self.context.__blobs__ = OOBTree()
        self.data[key] = item

    def create(self, key, overwrite = False):
        if key not in self or (key in self and overwrite):
            self[key] = BlobFile()
        return self[key]

    def formdata_dict(self, key):
        blob = self.get(key)
        if blob:
            return filedict(mimetype = blob.mimetype,
                            size = blob.size,
                            filename = blob.filename,
                            uid = None) #uid has to be there to make colander happy
            
    def create_from_formdata(self, key, value):
        """ Handle creation of a blob from a deform.FileUpload widget.
            Expects the following keys in value.
            
            fp
                A file stream
            filename
                Filename
            mimetype
                Mimetype
            
            if 'delete' is a present key and set to something that is true,
            data will be deleted.
            
        """
        if value:
            if value.get('delete'):
                if key in self:
                    del self[key]
            else:
                bf = self.create(key)
                with bf.blob.open('w') as f:
                    bf.filename = value['filename']
                    bf.mimetype = value['mimetype']
                    fp = value['fp']
                    bf.size = upload_stream(fp, f)
                return bf


class BlobFile(Persistent):
    size = None
    mimetype = ""
    filename = ""
    blob = None

    def __init__(self, size = None, mimetype = "", filename = ""):
        super(BlobFile, self).__init__()
        self.size = size
        self.mimetype = mimetype
        self.filename = filename
        self.blob = Blob()

#This will be moved
#FIXME: Make caching a choice
thumb_cache = LRUCache(100)


@implementer(IThumbnails)
@adapter(IThumbnailedContent)
class Thumbnails(object):
    """ Get a thumbnail image. A good place to add caching and similar in the future. """

    def __init__(self, context):
        self.context = context

    def get_thumb(self, scale, key = "image", direction = "thumb"):
        """ Return data from plone scale or None"""
        #Make cache optional
        cachekey = (self.context.uid, scale, key)
        cached = thumb_cache.get(cachekey)
        if cached:
            return cached
        scales = get_image_scales()
        maxwidth, maxheight = scales[scale]
        blobs = IBlobs(self.context)
        if key in blobs:
            registry = get_current_registry()
            if blobs[key].mimetype in registry.settings['supported_thumbnail_mimetypes']:
                with blobs[key].blob.open() as f:
                    try:
                        thumb_data, image_type, size = scaleImage(f, width = maxwidth, height = maxheight, direction = direction)
                    except IOError:
                        #FIXME: Logging?
                        return
                thumb = Thumbnail(thumb_data, image_type = image_type, size = size)
                thumb_cache.put(cachekey, thumb)
                return thumb

    def invalidate_context_cache(self):
        invalidate_keys = set()
        for k in thumb_cache.data.keys():
            if self.context.uid in k:
                invalidate_keys.add(k)
        for k in invalidate_keys:
            thumb_cache.invalidate(k)


class Thumbnail(object):
    width = 0
    height = 0
    image_type = u""
    image = None
    etag = ""

    def __init__(self, image, size = None, image_type = u""):
        self.width, self.height = size
        self.image = image
        self.image_type = image_type
        self.etag = str(uuid4())

    @property
    def mimetype(self):
        return "image/%s" % self.image_type


#Default image scales - mapped to twitter bootstrap columns
image_scales = {
    'icon': [20, 20],
    'mini': [40, 40],
    'col-1': [60, 120],
    'col-2': [160, 320],
    'col-3': [260, 520],
    'col-4': [360, 720],
    'col-5': [460, 920],
    'col-6': [560, 1120],
    'col-7': [660, 1320],
    'col-8': [760, 1520],
    'col-9': [860, 1720],
    'col-10': [960, 1920],
    'col-11': [1060, 2120],
    'col-12': [1160, 2320],
    }


def get_image_scales(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry._image_scales

def thumb_url(request, context, scale, key = 'image'):
    scales = get_image_scales(request.registry)
    if scale in scales:
        if IThumbnailedContent.providedBy(context):
            return request.resource_url(context, 'thumbnail', key, scale)

def find_all_db_objects(context):
    """ Return all objects stored in context.values(), and all subobjects.
        Great for reindexing the catalog or other database migrations.
    """
    #FIXME: This should be a generator instead. With a large database, it will require a lot of memory and time otherwise
    result = set()
    result.add(context)
    if hasattr(context, 'values'):
        for obj in context.values():
            result.update(find_all_db_objects(obj))
    return result

def get_dt_handler(request):
    return IDateTimeHandler(request)


@implementer(IDateTimeHandler)
@adapter(IRequest)
class DateTimeHandler(object):
    """ Handle conversion and printing of date and time.
    """
    locale = None
    timezone = None

    def __init__(self, request = None, tz_name = None, locale = None):
        if request is None:
            request = get_current_request()
        self.request = request
        if tz_name is None:
            tz_name = request.registry.settings.get('arche.timezone', 'UTC')
        try:
            self.timezone = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            self.timezone = pytz.timezone('UTC')
        if locale is None:
            locale = request.locale_name
        self.locale = locale

    def normalize(self, value):
        return self.timezone.normalize(value.astimezone(self.timezone))

    def format_dt(self, value, format='short', parts = 'dt', localtime = True):
        if localtime:
            dt = self.normalize(value)
        else:
            dt = value
        if parts == 'd':
            return format_date(dt, format = format, locale = self.locale)
        if parts == 't':
            return format_time(dt, format = format, locale = self.locale)
        return format_datetime(dt, format = format, locale = self.locale)

    def string_convert_dt(self, value, pattern = "%Y-%m-%dT%H:%M:%S"):
        """ Convert a string to a localized datetime. """
        return self.timezone.localize(datetime.strptime(value, pattern))

    def utcnow(self):
        return utcnow()

    def localnow(self):
        return datetime.now(self.timezone)

    def tz_to_utc(self, value):
        return value.astimezone(pytz.utc)

    def format_relative(self, value):
        """ Get a datetime object or a int() Epoch timestamp and return a
            pretty string like 'an hour ago', 'Yesterday', '3 months ago',
            'just now', etc
        """
        if isinstance(value, int):
            value = datetime.fromtimestamp(value, pytz.utc)
        #Check if timezone is naive, convert
        if value.tzinfo is None:
            raise ValueError("Not possible to use format_relative with timezone naive datetimes.")
        elif value.tzinfo is not pytz.utc:
            value = self.tz_to_utc(value)

        now = self.utcnow()
        diff = now - value
        second_diff = diff.seconds
        day_diff = diff.days

        if day_diff < 0:
            #FIXME: Shouldn't future be handled as well? :)
            return self.format_dt(value)

        if day_diff == 0:
            if second_diff < 10:
                return _("Just now")
            if second_diff < 60:
                return _("${diff} seconds ago", mapping={'diff': str(second_diff)})
            if second_diff < 120:
                return  _("1 minute ago")
            if second_diff < 3600:
                return _("${diff} minutes ago", mapping={'diff': str(second_diff / 60)})
            if second_diff < 7200:
                return _("1 hour ago")
            if second_diff < 86400:
                return _("${diff} hours ago", mapping={'diff': str(second_diff / 3600)})
        return self.format_dt(value)

def utcnow():
    """Get the current datetime localized to UTC.
    The difference between this method and datetime.utcnow() is
    that datetime.utcnow() returns the current UTC time but as a naive
    datetime object, whereas this one includes the UTC tz info."""
    return pytz.utc.localize(datetime.utcnow())

def invalidate_thumbs_in_context(context, event):
    IThumbnails(context).invalidate_context_cache()

def send_email(subject, recipients, html, sender = "noreply@localhost.com", plaintext = None, request = None, send_immediately = False, **kw):
    """ Send an email to users. This also checks the required settings and translates
        the subject.
        
        returns the message object sent, or None
    """
    if request is None:
        request = get_current_request()
    if isinstance(subject, TranslationString):
        subject = request.localizer.translate(subject)
    if isinstance(recipients, basestring):
        recipients = (recipients,)
    if plaintext is None:
        html2text = HTML2Text()
        html2text.ignore_links = True
        html2text.ignore_images = True
        html2text.body_width = 0
        plaintext = html2text.handle(html).strip()
    if not plaintext:
        plaintext = None #In case it was an empty string
    #It seems okay to leave sender blank since it's part of the default configuration
    msg = Message(subject = subject,
                  recipients = recipients,
                  sender = sender,
                  body = plaintext,
                  html = html,
                  **kw)
    mailer = get_mailer(request)
    #Note that messages are sent during the transaction process. See pyramid_mailer docs
    if send_immediately:
        mailer.send_immediately(msg)
    else:
        mailer.send(msg)
    return msg


class AttributeAnnotations(IterableUserDict):
    """ Handles a named storage for keys/values. It's always a named adapter
        and the name attribute should be the same as the name it was registered with. 
    """
    attr_name = None

    def __init__(self, context):
        self.context = context
        try:
            self.data = getattr(context, self.attr_name)
        except AttributeError:
            setattr(context, self.attr_name, OOBTree())
            self.data = getattr(context, self.attr_name)


@implementer(IRegistrationTokens)
@adapter(IRoot)
class RegistrationTokens(AttributeAnnotations):
    attr_name = '__registration_tokens__'

    def cleanup(self):
        expired = set()
        for (email, token) in self.items():
            if not token.valid:
                expired.add(email)
        for email in expired:
            del self[email]


@implementer(IJSONData)
@adapter(IBase)
class JSONData(object):
    """ Adater for creating json data from an IBase object.
        This is a prototype and might not be included later on.
    """

    def __init__(self, context):
        self.context = context

    def __call__(self, request, dt_formater = None, attrs = (), dt_atts = ()):
        normal_attrs = ['description', 'type_name',
                        'type_title', 'uid',
                        '__name__', 'size', 'mimetype']
        normal_attrs.extend(attrs)
        dt_attrs = ['created', 'modified']
        dt_attrs.extend(dt_attrs)
        #wf_state and name?
        results = {}
        results['icon'] = getattr(self.context, 'icon', 'file')
        results['tags'] = tuple(getattr(self.context, 'tags', ()))
        results['is_folder'] = IFolder.providedBy(self.context)
        title = getattr(self.context, 'title', None)
        if not title:
            title = self.context.__name__
        results['title'] = title
        for attr in normal_attrs:
            results[attr] = getattr(self.context, attr, '')
        for attr in dt_attrs:
            val = getattr(self.context, attr, '')
            if val and dt_formater:
                results[attr] = request.localizer.translate(dt_formater(val))
            else:
                results[attr] = val
        return results


class MIMETypeViews(IterableUserDict):

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            pass
        try:
            main_key = key.split('/')[0]
            return self.data["%s/*" % main_key]
        except KeyError:
            raise KeyError("Mime type %s wasn't found in views")

    def get(self, key, failobj=None):
        if key not in self:
            key = "%s/*" % key.split('/')[0]
            if key not in self:
                return failobj
        return self[key]

    def __contains__(self, key):
        return key in self.data or "%s/*" % key.split('/')[0] in self.data


def add_mimetype_view(config, mimetype, view_name):
    assert isinstance(mimetype, six.string_types), "%s is not a string" % mimetype
    assert isinstance(view_name, six.string_types), "%s is not a string" % view_name
    views = get_mimetype_views(config.registry)
    views[mimetype] = view_name

def get_mimetype_views(registry = None):
    if registry is None:
        registry = get_current_registry()
    try:
        return registry._mime_type_views
    except AttributeError:
        raise Exception("Mime type views must be registered first. Include 'arche.utils'")

_pil_codecs_to_mimetypes = {
    'jpeg_encoder': ('image/jpeg', 'image/pjpeg',),
    'zip_encoder': ('image/png',),
    'gif_encoder': ('image/gif',),
}
image_mime_to_title = {'image/jpeg': _("JPEG"),
                       'image/png': _("PNG"),
                       'image/gif': _("GIF")}
#FIXME: Add more codecs that work for web!

def check_supported_thumbnail_mimetypes():
    results = set()
    pil_methods = dir(pilcore)
    for (k, v) in _pil_codecs_to_mimetypes.items():
        if k in pil_methods:
            results.update(v)
    return results


def includeme(config):
    config.registry.registerAdapter(FlashMessages)
    config.registry.registerAdapter(Thumbnails)
    config.registry.registerAdapter(Blobs)
    config.registry.registerAdapter(DateTimeHandler)
    config.registry.registerAdapter(RegistrationTokens)
    config.registry.registerAdapter(JSONData)
    config.registry.registerAdapter(FileUploadTempStore)
    config.registry._content_factories = {}
    config.registry._content_schemas = {}
    config.registry._content_views = {}
    config.registry._image_scales = image_scales
    config.registry._addable_content = {}
    config.registry._addable_content = {}
    config.registry._mime_type_views = MIMETypeViews()
    config.add_directive('add_content_factory', add_content_factory)
    config.add_directive('add_addable_content', add_addable_content)
    config.add_directive('add_content_schema', add_content_schema)
    config.add_directive('add_content_view', add_content_view)
    config.add_directive('add_mimetype_view', add_mimetype_view)
    config.add_subscriber(invalidate_thumbs_in_context, [IThumbnailedContent, IObjectUpdatedEvent])
    config.registry.settings['supported_thumbnail_mimetypes'] = check_supported_thumbnail_mimetypes()

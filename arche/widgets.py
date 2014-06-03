from json import dumps
import string

from colander import null
from deform.widget import FileUploadWidget
from deform.widget import Select2Widget
from deform.widget import TextInputWidget
from pyramid.threadlocal import get_current_request 
from pyramid.traversal import find_resource
from repoze.catalog.query import Any

from arche import _
from arche.fanstatic_lib import dropzonebasiccss
from arche.fanstatic_lib import dropzonebootstrapcss
from arche.fanstatic_lib import dropzonecss
from arche.fanstatic_lib import dropzonejs


class TaggingWidget(Select2Widget):
    """ A very liberal widget that allows the user to pretty much enter anything.
        It will also display any existing values.
        
        placeholder
            Text to display when nothing is entered
        
        tags
            Predefined tags that will show up as suggestions
    """
    template = 'widgets/select2_tags'
    readonly_template = 'widgets/select2_tags' #XXX
    null_value = ''
    placeholder = _("Tags")
    minimumInputLength = 2
    tags = ()

    def serialize(self, field, cstruct, **kw):
        if cstruct in (null, None):
            cstruct = self.null_value
        readonly = kw.get('readonly', self.readonly)
        template = readonly and self.readonly_template or self.template
        #This formatting is kind of silly. Is there no smarter way to load old data into select2?
        current_data = dumps([{'text': x, 'id': x} for x in cstruct])
        available_tags = dumps(self.tags)
        tmpl_values = self.get_template_values(field, cstruct, kw)
        return field.renderer(template, available_tags = available_tags, current_data = current_data, **tmpl_values)

    def deserialize(self, field, pstruct):
        if pstruct in (null, self.null_value):
            return null
        return tuple(pstruct.split(','))


class ReferenceWidget(Select2Widget):
    """ A reference widget that searches for content to reference.
        It returns a list.
        
        Note! Any default values for this must return an iterator with uids.
        
        
        query_params
            Things to send to search.json page
            glob: 1 is always a good idea, since it enables search with glob
            type_name: Limit to these content types only. Either a list or a single name as a string.
    """
    template = 'widgets/select2_reference'
    readonly_template = 'widgets/select2_reference' #XXX
    null_value = ''
    placeholder = _("Type something to search.")
    minimumInputLength = 2
    show_thumbs = True
    default_query_params = {'glob': 1}
    query_params = {}
    #Make query view configurable?
    
    def _preload_data(self, field, cstruct):
        #XXX: Should this be moved to the json search view and invoked as a subrequest? Maybe
        view = field.schema.bindings['view']
        root = view.root
        query = root.catalog.query
        address_for_docid = root.document_map.address_for_docid
        results = []
        docids = query(Any('uid', cstruct))[1]
        for docid in docids:
            path = address_for_docid(docid)
            obj = find_resource(root, path)
            results.append({'id': obj.uid, 'text': obj.title})
        return dumps(results)

    def serialize(self, field, cstruct, **kw):
        view = field.schema.bindings['view']
        preload_data = "[]"
        if cstruct in (null, None):
            cstruct = self.null_value
        else:
            preload_data = self._preload_data(field, cstruct)
        readonly = kw.get('readonly', self.readonly)
        kw['placeholder'] = kw.get('placeholder', self.placeholder)
        kw['minimumInputLength'] = kw.get('minimumInputLength', self.minimumInputLength)
        kw['show_thumbs'] = str(kw.get('show_thumbs', self.show_thumbs)).lower() #true or false in js
        query_params = self.default_query_params.copy()
        query_params.update(self.query_params)
        query_url = view.request.resource_url(view.root, 'search.json', query = query_params)
        #FIXME: Support all kinds of keywords that the select2 widget supports?
        template = readonly and self.readonly_template or self.template
        tmpl_values = self.get_template_values(field, cstruct, kw)
        return field.renderer(template, preload_data = preload_data, query_url = query_url, **tmpl_values)

    def deserialize(self, field, pstruct):
        #Make sure pstruct follows query params?
        if pstruct in (null, self.null_value):
            return null
        return tuple(pstruct.split(','))


class DropzoneWidget(FileUploadWidget):
    """ All of the class attributes can be overridden in the widget.
    """
    maxFilesize = 100 # in Mb
    maxFiles = 1 # 'null' for infinite
    acceptedFiles = "image/png,image/*" #What's a sane default here? Where should it be configured?
    acceptedMimetypes = string.split(acceptedFiles, ',')
    
    dropzoneDefaultMessage = u'Drag and drop your files here'
    dropzoneFallbackMessage = u'dropzoneFallbackMessage'
    dropzoneFallbackText = u'dropzoneFallbackText'
    dropzoneInvalidFileType = u'dropzoneInvalidFileType'
    dropzoneFileTooBig = u'dropzoneFileTooBig'
    dropzoneResponseError = u'dropzoneResponseError'
    dropzoneCancelUpload = u'dropzoneCancelUpload'
    dropzoneCancelUploadConfirmation = u'dropzoneCancelUploadConfirmation'
    dropzoneRemoveFile = u'dropzoneRemoveFile'
    dropzoneMaxFilesExceeded = u'dropzoneMaxFilesExceeded'
    
    def serialize(self, field, cstruct=None, readonly=False):
        dropzonejs.need()
        #dropzonecss.need()
        dropzonebootstrapcss.need()
        dropzonebasiccss.need()
        field.request = get_current_request()
        field.hasfile = 'false'
        field.filename = ''
        field.filesize = 0
        if hasattr(field.request.context, '__blobs__') and field.request.context.__blobs__.has_key('file'):
            field.hasfile = 'true'
            field.filename = field.request.context.__blobs__.get('file').filename
            field.filesize = field.request.context.__blobs__.get('file').size
        return super(DropzoneWidget, self).serialize(field, cstruct=cstruct, readonly=readonly)

    def deserialize(self, field, pstruct=None):
        if pstruct is null:
            return null
        mimetype = self.tmpstore[pstruct]['mimetype']
        if mimetype in self.acceptedMimetypes or string.split(mimetype, '/')[0]+'/*' in self.acceptedMimetypes:
            return self.tmpstore[pstruct]
        return null


class EmbedWidget(TextInputWidget):
    template = 'widgets/embed_textinput'
    #readonly?

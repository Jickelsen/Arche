from repoze.catalog.query import Eq
from repoze.catalog.query import Contains
from repoze.catalog.query import Name
#from repoze.catalog.query import Any
from pyramid.traversal import resource_path
from pyramid.traversal import find_resource
from pyramid.view import view_config, view_defaults

from arche.views.base import BaseView
from arche import security
from arche import _


SEARCH_VIEW_QUERY = Eq('path', Name('path')) & Contains('searchable_text', Name('searchable_text'))


@view_defaults(permission = security.PERM_VIEW, context = 'arche.interfaces.IRoot')
class SearchView(BaseView):

    def _mk_query(self):
        self.docids = ()
        query = self.request.GET.get('query', None)
        if self.request.GET.get('glob', False):
            if '*' not in query:
                query = "%s*" % query
        if query:
            path = resource_path(self.context)
            query_vals = {'searchable_text': query,
                          'path': path}
            self.docids = self.root.catalog.query(SEARCH_VIEW_QUERY,
                                                  names = query_vals)[1]

    @view_config(name = 'search', renderer = 'arche:templates/search.pt')
    def search_page(self):
        self._mk_query()
        return {'results': self.result_objects()}

    @view_config(name = 'search.json', renderer = 'json')
    def search_json(self):
        self._mk_query()
        output = []
        for obj in self.result_objects():
            output.append({'text': obj.title, 'id': obj.uid})
        return {'results': output}

    def result_objects(self):
        for docid in self.docids:
            path = self.root.document_map.address_for_docid(docid)
            obj = find_resource(self.root, path)
            if self.request.has_permission(security.PERM_VIEW, obj):
                yield obj


def includeme(config):
    config.scan('.search')

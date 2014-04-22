from pyramid.httpexceptions import HTTPFound

from arche.views.base import DefaultAddForm
from arche.views.base import DefaultEditForm
from arche.views.base import BaseView
from arche import security
from arche import _


class UserAddForm(DefaultAddForm):
    type_name = u'User'

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        factory = self.get_content_factory(self.type_name)
        userid = appstruct.pop('userid')
        obj = factory(**appstruct)
        self.context[userid] = obj
        return HTTPFound(location = self.request.resource_url(obj))


class UserChangePasswordForm(DefaultEditForm):
    type_name = u'User'
    schema_name = u'change_password'

    def save_success(self, appstruct):
        #FIXME: pop old password
        return super(UserChangePasswordForm, self).save_success(appstruct)


class UsersView(BaseView):

    def __call__(self):
        return {'contents': [x for x in self.context.values()]}


class UserView(BaseView):

    def __call__(self):
        return {}


def includeme(config):
    config.add_view(UserAddForm,
                    context = 'arche.interfaces.IUsers',
                    name = 'add',
                    request_param = "content_type=User",
                    permission = security.PERM_MANAGE_USERS, #FIXME: Not add user perm?
                    renderer = 'arche:templates/form.pt')
    config.add_view(UserChangePasswordForm,
                    context = 'arche.interfaces.IUser',
                    name = 'change_password',
                    permission = security.PERM_EDIT, #FIXME: perm check in add
                    renderer = 'arche:templates/form.pt')
    config.add_view(UsersView,
                    name = 'view',
                    permission = security.PERM_MANAGE_USERS,
                    renderer = "arche:templates/content/users_table.pt",
                    context = 'arche.interfaces.IUsers')
    config.add_view(UserView,
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/content/user.pt",
                    context = 'arche.interfaces.IUser')



def includeme(config):
    config.include('arche.views.auth')
    config.include('arche.views.base')
    config.include('arche.views.contents')
    config.include('arche.views.listing')
    config.include('arche.views.initial_setup')
    config.include('arche.views.permissions')
    config.include('arche.views.users')
    config.include('arche.views.groups')

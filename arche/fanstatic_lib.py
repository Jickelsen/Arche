from fanstatic import Library
from fanstatic import Resource
from js.jquery import jquery
from js.bootstrap import bootstrap_css
from fanstatic.core import render_js

library = Library('arche', 'static')

main_css = Resource(library, 'main.css', depends = (bootstrap_css,))
dropzonejs = Resource(library, 'dropzone.js', depends=(jquery,))
dropzonecss = Resource(library, 'css/dropzone.css', depends=(dropzonejs,))
dropzonebootstrapcss = Resource(library, 'css/dropzone-bootstrap.css', depends=(dropzonejs,))
dropzonebasiccss = Resource(library, 'css/basic.css', depends=(dropzonejs,))

common_js = Resource(library, 'common.js', depends = (jquery,))
jqueryui = Resource(library, 'jquery-ui-1.10.4.min.js', depends=(jquery,)) #FIXME: Doesn't this exist in deform?
touchpunch_js = Resource(library, 'jquery.ui.touch-punch.min.js', depends = (jquery, jqueryui))
picturefill_js = Resource(library, "picturefill.js")

pure_js = Resource(library, 'pure.js', minified = 'pure.min.js', depends = (jquery,))


#IE8 fixes for Twitter Bootstrap
def render_conditional_comment_js(url, condition = 'lt', version = '9'):
    return '<!--[if %s IE %s]>%s<![endif]-->' % (condition, version, render_js(url))
html5shiv_js = Resource(library, "html5shiv.min.js", renderer = render_conditional_comment_js)
respond_js = Resource(library, "respond.min.js", renderer = render_conditional_comment_js)


"""

proxy2fs.py -- A mitmproxy script to write browsed files and requisite
resources to the filesystem as static .html.

Usage:

1. Configure browser to use mitmproxy for URLs
   (e.g. FoxyProxy whitelist patterns)

2. Launch mitmproxy with the proxy2fs.py inline script:

   .. code:: bash

        mitmproxy -s "proxy2fs.py <path/to/write/files/to>"

:author: Wes Turner
:license: MIT License

"""

import collections
import json
import os

from urlobject import URLObject

from mitmproxy.models import decoded


def start(context, argv):
    if len(argv) < 2:
        raise ValueError('Usage: proxy2fs.py <path/to/write/files/to>')
    elif len(argv) >= 2:
        context.dest_path = os.path.expanduser(argv[1])
        context.dirmode = 0o777
        if not os.path.exists(context.dest_path):
            os.makedirs(context.dest_path, mode=context.dirmode)
        context.include_host_in_path = False

    if len(argv) >= 3:
        context.include_host_in_path = True


def format_headers_as_list(obj):
    if obj:
        return [(k, v) for k, v in obj.fields]
    else:
        return None

MIMETYPE_TO_FILEEXT = {
    'text/html': 'html',
}


def joinpaths(*paths):
    _paths = []
    for p in paths:
        if os.path.isabs(p):
            p = p[1:]
        _paths.append(p)
    return os.path.join(*_paths)


def response(context, flow):
    if not hasattr(context, 'dest_path'):
        raise Exception('context.dest_path is unset')
    with decoded(flow.response):
        if (flow.response.status_code == 200):
            data = collections.OrderedDict()
            req = data['request'] = collections.OrderedDict()
            resp = data['response'] = collections.OrderedDict()
            req['headers'] = format_headers_as_list(flow.request.headers)
            resp['headers'] = format_headers_as_list(flow.response.headers)
            data['url'] = flow.request.url
            #data['content'] = flow.response.content
            data['host'] = flow.request.headers["Host"]
            data['content-type'] = flow.response.headers['Content-Type']
            data['filetype'] = data['content-type'].split(';', 1)[0]
            url = URLObject(data['url'])
            data['path'] = url.path
            _, fileext = os.path.splitext(data['path'])
            if data['path'].endswith('/'):
                filepath = data['path'] + 'index'
            else:
                filepath = data['path']
            if not fileext:
                fileext = MIMETYPE_TO_FILEEXT.get(data['filetype'])
                if fileext is not None:
                    filepath = "%s.%s" % (filepath, fileext)
            data['fileext'] = fileext
            data['filepath'] = filepath
            paths = [context.dest_path]
            if context.include_host_in_path:
                paths.append(data['host'])
            paths.append(data['filepath'])
            data['output_path'] = joinpaths(*paths)
            context.log(json.dumps(data, indent=2))

            output_dirname = os.path.dirname(data['output_path'])
            if not os.path.exists(output_dirname):
                os.makedirs(output_dirname, mode=context.dirmode)
            with file(data['output_path'], 'wb') as f:
                f.write(flow.response.content)

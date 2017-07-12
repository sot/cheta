from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import pickle
import zlib


@csrf_exempt
def remote_func(request):
    from . import remote_access

    try:
        func_info = pickle.loads(str(request.POST['func_info']))
        func = getattr(remote_access, func_info['func_name'])
        out = func(*func_info['args'], **func_info['kwargs'])

    except Exception as err:
        # Pass back any exception
        out = err

    stream = zlib.compress(pickle.dumps(out, protocol=-1))
    return HttpResponse(stream, content_type="application/octet-stream")

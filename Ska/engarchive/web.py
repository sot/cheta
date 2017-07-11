from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import pickle


@csrf_exempt
def remote_func(request):
    from . import remote_access

    func_info = pickle.loads(str(request.POST['func_info']))
    # print(func_info)
    func = getattr(remote_access, func_info['func_name'])
    out = func(*func_info['args'], **func_info['kwargs'])
    print("HELLO2")
    print(out)

    return HttpResponse(pickle.dumps(out, protocol=-1),
                        content_type="application/octet-stream")

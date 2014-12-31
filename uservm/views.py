from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models.fields.related import RelatedObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render
from jsonview.decorators import json_view

from uservm.models import VirtualMachine

_NO_CONTENT = HttpResponse(status=204)

def _vm_for_request(request):
    user = request.user
    if not user.is_authenticated():
        raise PermissionDenied('User is not logged in')
    try:
        return user.virtualmachine
    except RelatedObjectDoesNotExist:
        return VirtualMachine.create(user)

@login_required
def home(request):
    return render(request, 'home.html', _vm_for_request(request).status())

@json_view
def status(request):
    return _vm_for_request(request).status()

@json_view
def start(request):
    vm = _vm_for_request(request)
    vm.start()
    return vm.status()

@json_view
def stop(request):
    _vm_for_request(request).stop()
    return _NO_CONTENT

@json_view
def shutdown(request):
    _vm_for_request(request).shutdown()
    return _NO_CONTENT

@json_view
def reset(request):
    _vm_for_request(request).reset()
    return _NO_CONTENT

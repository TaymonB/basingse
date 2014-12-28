import logging

from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone

from uservm.ehutils import api_call, exceptions, POST, EMPTY_RESP

logger = logging.getLogger(__name__)

class VirtualMachine(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    server_uuid = models.CharField(max_length=36)
    drive_uuid = models.CharField(max_length=36)
    last_heartbeat = models.DateTimeField(null=True)

    @classmethod
    def create(cls, user):
        vm = cls(user=user)
        vm.provision_drive()
        vm.provision_server()
        vm.save()
        return vm

    def destroy(self):
        self.delete()
        try:
            api_call(('servers', self.server_uuid, 'destroy'), POST, EMPTY_RESP)
        except exceptions.ElastichostsMissingError:
            logger.error('Server %s for VM %d is already gone', self.server_uuid, self.id)
        try:
            api_call(('drives', self.drive_uuid, 'destroy'), POST, EMPTY_RESP)
        except exceptions.ElastichostsMissingError:
            logger.error('Drive %s for VM %d is already gone', self.drive_uuid, self.id)

    def provision_drive(self):
        template_drive_uuid, = (drive['drive'] for drive in api_call(('drives', 'info'))
                                if drive['name'] == 'BASINGSE_TEMPLATE')
        params = {'size': '2G', 'tags': 'basingse'}
        self.drive_uuid = api_call(('drives', 'create'), params)['drive']
        return api_call(('drives', self.drive_uuid, 'image', template_drive_uuid), POST)

    def provision_server(self, start=False):
        params = {'cpu': 500, 'smp': 'auto', 'mem': 256, 'persistent': True, 'ide:0:0': self.drive_uuid,
                  'boot': 'ide:0:0', 'nic:0:model': 'e1000', 'nic:0:dhcp': 'auto', 'vnc': 'auto', 'tags': 'basingse'}
        if start:
            info = api_call(('servers', 'create'), params)
        else:
            info = api_call(('servers', 'create', 'stopped'), params)
        self.server_uuid = info['server']
        return info

    def start(self):
        api_call(('servers', self.server_uuid, 'start'), POST)
        self.heartbeat()

    def heartbeat(self):
        self.last_heartbeat = timezone.now()

    def stop(self):
        self.last_heartbeat = None
        api_call(('servers', self.server_uuid, 'stop'), POST, EMPTY_RESP)

    def status(self):
        server_status = api_call(('servers', self.server_uuid, 'info'))['status']
        if server_status == 'stopped' and check_drive:
            return api_call(('drives', self.drive_uuid, 'info', 'full')).get('imaging', 'stopped')
        else:
            return server_status

from django.conf import settings
from django.core import signing
from django.db import models

from uservm.eh_utils import api_call, POST, EMPTY_RESP

class VirtualMachine(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    server_uuid = models.CharField(max_length=36)
    drive_uuid = models.CharField(max_length=36)
    last_heartbeat = models.DateTimeField(null=True)

    @classmethod
    def provision(cls, user):
        template_drive_uuid, = (drive['drive'] for drive in api_call(('drives', 'info'))
                                if drive['name'] == 'BASINGSE_TEMPLATE')
        drive_uuid = api_call(('drives', 'create'), {'size': '2G'})['drive']
        api_call(('drives', drive_uuid, 'image', template_drive_uuid), POST)
        server_uuid = api_call(('servers', 'create', 'stopped'),
                               {'cpu': 500, 'smp': 'auto', 'mem': 256, 'persistent': True,
                                'ide:0:0': drive_uuid, 'boot': 'ide:0:0', 'nic:0:model': 'e1000',
                                'nic:0:dhcp': 'auto', 'vnc': 'auto'})['server']
        vm = cls(user=user, server_uuid=server_uuid, drive_uuid=drive_uuid)
        vm.save()
        custom_config = {'user:basingse': signing.Signer().sign(vm.id)}
        api_call(('servers', server_uuid, 'set'), custom_config)
        api_call(('drives', drive_uuid, 'set'), custom_config)
        return vm

    def destroy(self):
        self.delete()
        api_call(('servers', self.server_uuid, 'destroy'), POST, EMPTY_RESP)
        api_call(('drives', self.drive_uuid, 'destroy'), POST, EMPTY_RESP)

    def start(self):
        api_call(('servers', self.server_uuid, 'start'), POST)
        heartbeat()

    def heartbeat(self):
        self.last_heartbeat = datetime.datetime.now()
        self.save()

    def status(self, check_drive=True):
        server_status = api_call(('servers', self.server_uuid, 'info'))['status']
        if server_status == 'stopped' and check_drive:
            return api_call(('drives', self.drive_uuid, 'info', 'full')).get('imaging', 'stopped')
        else:
            return server_status

    def stop(self):
        self.last_heartbeat = None
        self.save()
        api_call(('servers', self.server_uuid, 'stop'), POST, EMPTY_RESP)

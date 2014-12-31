import logging

from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import crypto, timezone

from uservm.ehutils import api_call, exceptions, GET, POST, EMPTY_RESP, OBJECT_RESP

logger = logging.getLogger(__name__)

RETRY, REPROVISION, RERAISE = enum.Enum('MissingResourceHandler', ('retry', 'reprovision', 'reraise'))

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
        self.destroy_server()
        self.destroy_drive()

    def provision_server(self, started=False):
        params = {'cpu': 500, 'smp': 'auto', 'mem': 256, 'persistent': True, 'ide:0:0': self.drive_uuid,
                  'boot': 'ide:0:0', 'nic:0:model': 'e1000', 'nic:0:dhcp': 'auto', 'vnc': 'auto',
                  'password': crypto.get_random_string(8), 'user:basingse': settings.PUBLIC_UNIQUE_ID}
        if started:
            info = api_call(('servers', 'create'), params)
        else:
            info = api_call(('servers', 'create', 'stopped'), params)
        self.server_uuid = info['server']
        return info

    def provision_drive(self):
        template_drive_uuid, = (drive['drive'] for drive in api_call(('drives', 'info'))
                                if drive['name'] == 'BASINGSE_TEMPLATE')
        params = {'size': '2G', 'user:basingse': settings.PUBLIC_UNIQUE_ID}
        self.drive_uuid = api_call(('drives', 'create'), params)['drive']
        return self.api_call_on_drive(('image', template_drive_uuid), POST, missing_drive='reraise')

    def api_call_on_server(self, action, data=GET, expected=OBJECT_RESP, gzip_data=True,
                           missing_server=RETRY, missing_drive=RETRY):
        if isinstance(action, str):
            resource = ('servers', self.server_uuid, action)
        else:
            resource = ('servers', self.server_uuid) + tuple(action)
        try:
            try:
                return api_call(resource, data, expected, gzip_data)
            except exceptions.ElastichostsMissingError:
                if missing_server == RETRY:
                    self.reprovision_missing_server()
                    return api_call(resource, data, expected, gzip_data)
                elif missing_server == REPROVISION:
                    return self.reprovision_missing_server()
                elif missing_server == RERAISE:
                    raise
                else:
                    return missing_server()
        except exceptions.ElastichostsFailedError as err:
            if (missing_drive != RERAISE and
                (self.drive_uuid in str(err) or
                 api_call(('servers', self.server_uuid, 'info')).get('ide:0:0') != self.drive_uuid)):
                if missing_drive == RETRY:
                    self.reprovision_missing_drive()
                    return api_call(resource, data, expected, gzip_data)
                elif missing_drive == REPROVISION:
                    return self.reprovision_missing_drive()
                else:
                    return missing_drive()
            else:
                raise

    def api_call_on_drive(self, action, data=GET, expected=OBJECT_RESP, gzip_data=True, missing_drive=RETRY):
        if isinstance(action, str):
            resource = ('drives', self.server_uuid, action)
        else:
            resource = ('drives', self.server_uuid) + tuple(action)
        try:
            return api_call(resource, data, expected, gzip_data)
        except exceptions.ElastichostsMissingError:
            if missing_drive == RETRY:
                self.reprovision_missing_drive()
                return api_call(resource, data, expected, gzip_data)
            elif missing_drive == REPROVISION:
                return self.reprovision_missing_drive()
            elif missing_drive == RERAISE:
                raise
            else:
                return missing_drive()

    def reprovision_missing_server(self, started=False):
        logger.error('Server %s for VM %d not found, reprovisioning', (self.server_uuid, self.id))
        info = self.provision_server(started)
        self.save(update_fields=('server_uuid',))
        return info

    def reprovision_missing_drive(self):
        logger.error('Drive %s for VM %d not found, reprovisioning', (self.drive_uuid, self.id))
        info = self.provision_drive()
        self.save(update_fields=('drive_uuid',))
        self.api_call_on_server('set', {'ide:0:0': self.drive_uuid}, missing_server=REPROVISION, missing_drive=RERAISE)
        return info

    def get_server_info(self):
        return self.api_call_on_server('info', missing_server=REPROVISION)

    def get_drive_info(self):
        return self.api_call_on_server('info', missing_drive=REPROVISION)

    def destroy_server(self):
        self.api_call_on_server('destroy', POST, EMPTY_RESP,
                                missing_server=lambda: logger.error('Server %s for VM %d is already gone',
                                                                    self.server_uuid, self.id))

    def destroy_drive(self):
        self.api_call_on_drive('destroy', POST, EMPTY_RESP,
                               missing_drive=lambda: logger.error('Drive %s for VM %d is already gone',
                                                                  self.drive_uuid, self.id))

    def start(self):
        def missing_drive():
            self.reprovision_missing_drive()
            raise exceptions.ElastichostsBusyError('drive newly reprovisioned')
        info = self.api_call_on_server('start', POST,
                                       missing_server=lambda: self.reprovision_missing_server(True),
                                       missing_drive=missing_drive)
        self.heartbeat()
        return info

    def stop(self):
        self.api_call_on_server('stop', POST, EMPTY_RESP)
        self.heartbeat(False)

    def shutdown(self):
        self.api_call_on_server('shutdown', POST, EMPTY_RESP, missing_server=REPROVISION)

    def reset(self):
        self.api_call_on_server('reset', POST, EMPTY_RESP, missing_server=REPROVISION)

    def status(self):
        status = {}
        server_info = self.get_server_info()
        state = info['status']
        if state == 'active':
            status['address'] = info['vnc:ip']
            status['password'] = info['password']
        elif state == 'stopped':
            if self.last_heartbeat is not None:
                self.heartbeat(False)
            imaging = self.api_call_on_drive(('info', 'full')).get('imaging')
            if imaging == 'queued':
                state = 'queued'
            elif imaging is None:
                pass
            elif imaging.endswith('%'):
                state = 'imaging'
                status['percent'] = int(drive_state[:-1])
            else:
                logger.error('Drive %s for VM %d has problematic imaging status %s',
                             self.server_uuid, self.id, imaging)
        else:
            logger.error('Server %s for VM %d has problematic status %s, powering off',
                         self.server_uuid, self.id, state)
            self.stop()
            state = 'stopped'
        status['state'] = state
        return status

    def heartbeat(self, active=True):
        if active:
            self.last_heartbeat = timezone.now()
        else:
            self.last_heartbeat = None
        self.save(update_fields=('last_heartbeat',))

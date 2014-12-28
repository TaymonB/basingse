import datetime

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import timezone

from uservm.ehutils import api_call, POST, EMPTY_RESP
from uservm.models import VirtualMachine

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        servers = {server['server']: server for server in api_call(('servers', 'info'))
                   if server.get('user:basingse') == settings.PUBLIC_UNIQUE_ID}
        drives = {drive['drive']: drive for drive in api_call(('drives', 'info', 'full'))
                  if drive.get('user:basingse') == settings.PUBLIC_UNIQUE_ID}
        for vm in VirtualMachine.objects.all():
            was_left_on = vm.last_heartbeat is not None
            should_stay_on = was_left_on and timezone.now() - vm.last_heartbeat < datetime.timedelta(hours=1)
            try:
                drive = drives.pop(vm.drive_uuid)
            except KeyError:
                self.stderr.write('Drive %s for VM %d not found, reprovisioning' % (vm.drive_uuid, vm.id))
                drive = vm.provision_drive()
            try:
                server = servers.pop(vm.server_uuid)
                status = server['status']
            except KeyError:
                self.stderr.write('Server %s for VM %d not found, reprovisioning (initially %s)' %
                                  (vm.server_uuid, vm.id, 'on' if should_stay_on else 'off'))
                server = vm.provision_server(should_stay_on)
                status = 'active' if should_stay_on else 'stopped'
            if status == 'active':
                if not should_stay_on:
                    if not was_left_on:
                        self.stderr.write("Server %s for VM %d shouldn't be on, powering off" %
                                          (vm.server_uuid, vm.id))
                    vm.stop()
            elif status == 'stopped':
                vm.last_heartbeat = None
            else:
                self.stderr.write('Server %s for VM %d has problematic status %s, powering off' %
                                  (vm.server_uuid, vm.id, status))
                vm.stop()
            vm.save()
        for server_uuid in servers:
            self.stderr.write("Server %s doesn't belong to a VM, destroying" % server_uuid)
            api_call(('servers', server_uuid, 'destroy'), POST, EMPTY_RESP)
        for drive_uuid in drives:
            self.stderr.write("Drive %s doesn't belong to a VM, destroying" % drive_uuid)
            api_call(('drives', drive_uuid, 'destroy'), POST, EMPTY_RESP)

import datetime
import logging

logger = logging.getLogger(__name__)

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
            should_stay_on = was_left_on and timezone.now() - vm.last_heartbeat < datetime.timedelta(minutes=20)
            try:
                drive = drives.pop(vm.drive_uuid)
            except KeyError:
                drive = vm.reprovision_missing_drive()
            try:
                server = servers.pop(vm.server_uuid)
            except KeyError:
                server = vm.reprovision_missing_server()
            state = server['status']
            if state == 'active':
                if not should_stay_on:
                    if not was_left_on:
                        logger.error("Server %s for VM %d shouldn't be on, powering off",
                                     vm.server_uuid, vm.id)
                    vm.stop()
            elif state == 'stopped':
                if was_left_on:
                    vm.heartbeat(False)
            else:
                logger.error('Server %s for VM %d has problematic status %s, powering off',
                             vm.server_uuid, vm.id, state)
                vm.stop()
        for server_uuid in servers:
            logger.error("Server %s doesn't belong to a VM, destroying", server_uuid)
            api_call(('servers', server_uuid, 'destroy'), POST, EMPTY_RESP)
        for drive_uuid in drives:
            logger.error("Drive %s doesn't belong to a VM, destroying", drive_uuid)
            api_call(('drives', drive_uuid, 'destroy'), POST, EMPTY_RESP)

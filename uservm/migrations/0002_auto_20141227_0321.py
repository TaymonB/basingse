# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('uservm', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='virtualmachine',
            old_name='drive_id',
            new_name='drive_uuid',
        ),
        migrations.RenameField(
            model_name='virtualmachine',
            old_name='server_id',
            new_name='server_uuid',
        ),
        migrations.AddField(
            model_name='virtualmachine',
            name='last_heartbeat',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
    ]

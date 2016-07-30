# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0026_delete_mituser'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutgoingWebhookBot',
            fields=[
                ('userprofile_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('post_url', models.TextField()),
                ('service_api_key', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=('zerver.userprofile',),
        ),
    ]

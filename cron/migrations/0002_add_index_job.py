# Generated by Django 5.1.5 on 2025-02-05 17:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cron', '0001_create_job'),
        ('web', '0004_add_type_activitylog'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='job',
            options={'ordering': ('scheduled_at',)},
        ),
        migrations.AddIndex(
            model_name='job',
            index=models.Index(
                fields=['scheduled_at'], name='cron_job_schedul_26ecb0_idx'
            ),
        ),
    ]

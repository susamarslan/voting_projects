
from django.db import migrations, models


def _rls(schema_editor, action):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(f'ALTER TABLE IF EXISTS "polls_ratelimit" {action} ROW LEVEL SECURITY')


def enable_rls(apps, schema_editor):
    _rls(schema_editor, "ENABLE")


def disable_rls(apps, schema_editor):
    _rls(schema_editor, "DISABLE")


class Migration(migrations.Migration):

    dependencies = [
        ('polls', '0003_poll_ends_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='RateLimit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=128, unique=True, verbose_name='anahtar')),
                ('count', models.PositiveIntegerField(default=0, verbose_name='sayı')),
                ('expires_at', models.DateTimeField(db_index=True, verbose_name='bitiş')),
            ],
            options={
                'verbose_name': 'hız sınırı sayacı',
                'verbose_name_plural': 'hız sınırı sayaçları',
            },
        ),
        migrations.AddField(
            model_name='poll',
            name='members_only',
            field=models.BooleanField(default=False, help_text='Açıksa misafirler oy veremez.', verbose_name='yalnızca üyeler'),
        ),
        migrations.RunPython(enable_rls, disable_rls),
    ]

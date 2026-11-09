"""Supabase'de tüm Django tablolarında Row Level Security'yi açar.

Supabase, public şemasındaki tabloları otomatik olarak REST API'si (PostgREST)
üzerinden açar. RLS açık ve hiç politika yokken bu API'den anon/authenticated
rolleriyle hiçbir satır okunamaz/yazılamaz. Django, tablo sahibi olan postgres
rolüyle bağlandığı için RLS'ten etkilenmez; bu yüzden politika eklenmez.

Yalnızca PostgreSQL'de çalışır; SQLite'ta hiçbir şey yapmaz.
YENİ BİR MODEL/TABLO EKLENİRSE: onun için de RLS açan yeni bir migration yaz.
"""

from django.db import migrations

TABLES = [
    # accounts
    "accounts_user",
    "accounts_user_groups",
    "accounts_user_user_permissions",
    # auth
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    # admin
    "django_admin_log",
    # contenttypes
    "django_content_type",
    # sessions
    "django_session",
    # migrate komutunun kendi tablosu
    "django_migrations",
    # polls
    "polls_poll",
    "polls_option",
    "polls_vote",
]


def _run(schema_editor, action):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f'ALTER TABLE IF EXISTS "{table}" {action} ROW LEVEL SECURITY')


def enable_rls(apps, schema_editor):
    _run(schema_editor, "ENABLE")


def disable_rls(apps, schema_editor):
    _run(schema_editor, "DISABLE")


class Migration(migrations.Migration):
    dependencies = [
        ("polls", "0001_initial"),
        ("accounts", "0001_initial"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("sessions", "0001_initial"),
    ]

    operations = [migrations.RunPython(enable_rls, disable_rls)]

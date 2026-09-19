from django.db import migrations

LEAVE_TYPES = [
    {
        'code': 'CL',
        'name': 'Casual Leave',
        'description': 'Short personal leave for unforeseen needs.',
        'max_days_per_year': 12,
        'applicable_to': 'ALL',
        'requires_document': False,
        'sort_order': 1,
    },
    {
        'code': 'EL',
        'name': 'Earned Leave',
        'description': 'Privilege leave earned through service.',
        'max_days_per_year': 30,
        'applicable_to': 'ALL',
        'requires_document': False,
        'sort_order': 2,
    },
    {
        'code': 'ML',
        'name': 'Medical Leave',
        'description': 'Leave on medical grounds. A supporting document may be required.',
        'max_days_per_year': 15,
        'applicable_to': 'ALL',
        'requires_document': True,
        'sort_order': 3,
    },
    {
        'code': 'DL',
        'name': 'Duty Leave',
        'description': 'Official duty assigned by the university.',
        'max_days_per_year': None,
        'applicable_to': 'ALL',
        'requires_document': False,
        'sort_order': 4,
    },
    {
        'code': 'RH',
        'name': 'Restricted Holiday',
        'description': 'Optional restricted holiday as notified by the university.',
        'max_days_per_year': 2,
        'applicable_to': 'ALL',
        'requires_document': False,
        'sort_order': 5,
    },
]


def seed_leave_types(apps, schema_editor):
    LeaveType = apps.get_model('leaves', 'LeaveType')
    for item in LEAVE_TYPES:
        LeaveType.objects.update_or_create(code=item['code'], defaults=item)


def unseed_leave_types(apps, schema_editor):
    LeaveType = apps.get_model('leaves', 'LeaveType')
    LeaveType.objects.filter(code__in=[item['code'] for item in LEAVE_TYPES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('leaves', '0001_initial_leave_models'),
    ]

    operations = [
        migrations.RunPython(seed_leave_types, unseed_leave_types),
    ]

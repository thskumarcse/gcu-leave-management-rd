from django.db import migrations, models
from django.db.models import Sum


def backfill_baseline_used(apps, schema_editor):
    LeaveCredit = apps.get_model('leaves', 'LeaveCredit')
    LeaveApplication = apps.get_model('leaves', 'LeaveApplication')
    for credit in LeaveCredit.objects.all():
        used = LeaveApplication.objects.filter(
            employee_id=credit.employee_id,
            leave_type_id=credit.leave_type_id,
            start_date__year=credit.year,
            status__in=['PENDING', 'APPROVED'],
        ).aggregate(total=Sum('days'))['total'] or 0
        credit.baseline_used = used
        credit.save(update_fields=['baseline_used'])


def unfill_baseline_used(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('leaves', '0007_account_is_operator_and_leave_credit'),
    ]

    operations = [
        migrations.AddField(
            model_name='leavecredit',
            name='baseline_used',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=6),
        ),
        migrations.RunPython(backfill_baseline_used, unfill_baseline_used),
    ]

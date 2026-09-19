import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('employees', '0002_align_employee_csv_schema'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('title', models.CharField(max_length=160)),
                ('message', models.CharField(max_length=400)),
                ('link', models.CharField(blank=True, max_length=200)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'employee',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notifications',
                        to='employees.employee',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['employee', 'is_read'],
                name='notificatio_employe_c4b2a1_idx',
            ),
        ),
    ]

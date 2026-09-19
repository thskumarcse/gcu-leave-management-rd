from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='is_admin',
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name='account',
            index=models.Index(fields=['is_admin'], name='accounts_ac_is_admi_7c9a2e_idx'),
        ),
    ]

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='paper',
            name='year',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='paper',
            name='summary',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='paper',
            name='total_pages',
            field=models.IntegerField(default=0),
        ),
    ]

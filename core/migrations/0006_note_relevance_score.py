# Generated manually for adding relevance_score field to Note model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_remove_note_embedding_remove_note_relevance_score'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='relevance_score',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
    ]

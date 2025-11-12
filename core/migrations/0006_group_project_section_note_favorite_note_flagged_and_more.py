# Generated manually to fix migration issues

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_alter_researchsession_status'),
    ]

    operations = [
        # Create Project model
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),

        # Create Section model
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='core.project')),
            ],
            options={
                'ordering': ['order', 'created_at'],
            },
        ),

        # Create Group model
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_groups', to='core.project')),
                ('section', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='groups', to='core.section')),
            ],
            options={
                'ordering': ['order', 'created_at'],
            },
        ),

        # Add user interaction fields to Note
        migrations.AddField(
            model_name='note',
            name='favorite',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='note',
            name='flagged',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='note',
            name='user_annotations',
            field=models.TextField(blank=True),
        ),

        # Add organization fields to Note
        migrations.AddField(
            model_name='note',
            name='groups',
            field=models.ManyToManyField(blank=True, related_name='notes', to='core.group'),
        ),
        migrations.AddField(
            model_name='note',
            name='projects',
            field=models.ManyToManyField(blank=True, related_name='notes', to='core.project'),
        ),
        migrations.AddField(
            model_name='note',
            name='sections',
            field=models.ManyToManyField(blank=True, related_name='notes', to='core.section'),
        ),

        # Add indexes with new naming convention
        migrations.AddIndex(
            model_name='note',
            index=models.Index(fields=['paper'], name='core_note_paper_i_1a9b04_idx'),
        ),
        migrations.AddIndex(
            model_name='note',
            index=models.Index(fields=['note_type'], name='core_note_note_ty_23f892_idx'),
        ),
        migrations.AddIndex(
            model_name='note',
            index=models.Index(fields=['status'], name='core_note_status_4b8c5c_idx'),
        ),
        migrations.AddIndex(
            model_name='note',
            index=models.Index(fields=['created_at'], name='core_note_created_3e1589_idx'),
        ),
        migrations.AddIndex(
            model_name='paper',
            index=models.Index(fields=['session'], name='core_paper_session_cd0ed6_idx'),
        ),
        migrations.AddIndex(
            model_name='paper',
            index=models.Index(fields=['status'], name='core_paper_status_9f42c2_idx'),
        ),
        migrations.AddIndex(
            model_name='paper',
            index=models.Index(fields=['created_at'], name='core_paper_created_898537_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['created_at'], name='core_projec_created_1f5557_idx'),
        ),
        migrations.AddIndex(
            model_name='researchsession',
            index=models.Index(fields=['status'], name='core_resear_status_fecc07_idx'),
        ),
        migrations.AddIndex(
            model_name='researchsession',
            index=models.Index(fields=['created_at'], name='core_resear_created_cea7d9_idx'),
        ),
        migrations.AddIndex(
            model_name='section',
            index=models.Index(fields=['project'], name='core_sectio_project_cf9c62_idx'),
        ),
        migrations.AddIndex(
            model_name='group',
            index=models.Index(fields=['section'], name='core_group_section_3eb4f1_idx'),
        ),
        migrations.AddIndex(
            model_name='group',
            index=models.Index(fields=['project'], name='core_group_project_2b7da0_idx'),
        ),
    ]

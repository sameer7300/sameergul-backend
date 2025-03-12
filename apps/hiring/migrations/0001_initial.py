# Generated by Django 4.2.19 on 2025-02-26 16:09

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HiringRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('requirements', models.TextField()),
                ('deadline', models.DateField(blank=True, null=True)),
                ('budget', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('in_review', 'In Review'), ('approved', 'Approved'), ('quoted', 'Price Quoted'), ('accepted', 'Quote Accepted'), ('rejected', 'Quote Rejected'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='draft', max_length=20)),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')], default='medium', max_length=20)),
                ('quoted_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('final_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('admin_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PriceModifier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('modifier_type', models.CharField(choices=[('multiplier', 'Multiplier'), ('fixed', 'Fixed Amount'), ('percentage', 'Percentage')], default='percentage', max_length=20)),
                ('value', models.DecimalField(decimal_places=2, help_text='For multiplier: 1.5 means 50% increase. For percentage: 15 means 15% increase.', max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ServiceType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('base_price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='RequestStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('in_review', 'In Review'), ('approved', 'Approved'), ('quoted', 'Price Quoted'), ('accepted', 'Quote Accepted'), ('rejected', 'Quote Rejected'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], max_length=20)),
                ('new_status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('in_review', 'In Review'), ('approved', 'Approved'), ('quoted', 'Price Quoted'), ('accepted', 'Quote Accepted'), ('rejected', 'Quote Rejected'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='request_status_changes', to=settings.AUTH_USER_MODEL)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='hiring.hiringrequest')),
            ],
            options={
                'verbose_name_plural': 'Request status histories',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RequestMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('is_internal', models.BooleanField(default=False, help_text='If true, only admins can see this message')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='hiring.hiringrequest')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_request_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='RequestAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='hiring/attachments/')),
                ('description', models.CharField(blank=True, max_length=200)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='hiring.hiringrequest')),
            ],
        ),
        migrations.AddField(
            model_name='hiringrequest',
            name='applied_modifiers',
            field=models.ManyToManyField(blank=True, related_name='requests', to='hiring.pricemodifier'),
        ),
        migrations.AddField(
            model_name='hiringrequest',
            name='service_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='requests', to='hiring.servicetype'),
        ),
        migrations.AddField(
            model_name='hiringrequest',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hiring_requests', to=settings.AUTH_USER_MODEL),
        ),
    ]

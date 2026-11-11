from unicodedata import normalize

from django.db import migrations, models


def populate_names(apps, schema_editor):
    Organization = apps.get_model("hub", "Organization")
    for organization in Organization.objects.all():
        organization.normalized_name = normalize("NFKC", organization.name).casefold()
        organization.save(update_fields=["normalized_name"])


class Migration(migrations.Migration):
    dependencies = [("hub", "0002_activity_seed_key_and_more")]
    operations = [
        migrations.AddField(
            model_name="organization",
            name="normalized_name",
            field=models.CharField(max_length=360, null=True, editable=False),
        ),
        migrations.RunPython(populate_names, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="organization",
            name="normalized_name",
            field=models.CharField(max_length=360, unique=True, editable=False),
        ),
    ]

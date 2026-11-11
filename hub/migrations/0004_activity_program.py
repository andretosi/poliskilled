from django.db import migrations, models


def correct_program(apps, schema_editor):
    Organization = apps.get_model("hub", "Organization")
    Activity = apps.get_model("hub", "Activity")
    legacy = Organization.objects.filter(name__iexact="Passion in Action")
    for old in legacy:
        poli, _ = Organization.objects.get_or_create(
            normalized_name="politecnico di milano",
            defaults={
                "name": "Politecnico di Milano",
                "short_name": "Polimi",
                "website": "https://www.polimi.it/",
                "verified": True,
            },
        )
        if not poli.verified:
            raise RuntimeError(
                "Verificare manualmente l'identità del Politecnico di Milano "
                "prima della migrazione."
            )
        for activity in Activity.objects.filter(organizations=old):
            activity.organizations.add(poli)
            activity.program = "passion"
            activity.save(update_fields=["program"])
        # Memberships are deliberately NOT transferred to the university.
        old.delete()
    Activity.objects.filter(
        source_url__startswith="https://www.polimi.it/formazione/passion-in-action"
    ).update(program="passion")


class Migration(migrations.Migration):
    dependencies = [("hub", "0003_organization_normalized_name")]
    operations = [
        migrations.AddField(
            model_name="activity",
            name="program",
            field=models.CharField(
                "programma",
                max_length=20,
                blank=True,
                choices=[("", "Nessuno"), ("passion", "Passion in Action")],
            ),
        ),
        # Identity consolidation cannot be reversed without the pre-migration backup.
        migrations.RunPython(correct_program),
    ]

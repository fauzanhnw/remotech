from django.db import migrations, models
from django.db.models import Exists, F, OuterRef, Subquery


def backfill_submitted_on(apps, schema_editor):
    """Salin nilai `submit_on` lama ke `submitted_on`.

    - Upload (assignment terisi): selalu final saat create → salin apa adanya.
    - Quiz (assignment NULL): final hanya bila progress module berstatus
      FINISH (student pernah menyelesaikan quiz); draft quiz lama tetap NULL.
    """
    Submission = apps.get_model("remotech", "Submission")
    UserAnswer = apps.get_model("remotech", "UserAnswer")
    UserProgress = apps.get_model("remotech", "UserProgress")

    Submission.objects.filter(assignment__isnull=False).update(
        submitted_on=F("submit_on")
    )

    module_of_first_answer = (
        UserAnswer.objects.filter(submission_id=OuterRef("pk"))
        .values("question__module_id")[:1]
    )
    finish_exists = UserProgress.objects.filter(
        user_id=OuterRef("user_id"),
        module_id=Subquery(module_of_first_answer),
        status="finish",
    )
    Submission.objects.filter(assignment__isnull=True).annotate(
        finished=Exists(finish_exists)
    ).filter(finished=True).update(submitted_on=F("submit_on"))


class Migration(migrations.Migration):

    dependencies = [
        ("remotech", "0016_coursemodule_due_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="submitted_on",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_submitted_on, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="submission",
            name="submit_on",
        ),
    ]

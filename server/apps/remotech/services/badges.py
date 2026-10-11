from server.apps.remotech.models import (
    Badge,
    CourseModule,
    UserBadge,
    UserProgress,
)


def sync_badges(user, course):
    """Evaluasi badge otomatis (rule_type `course_complete`) untuk user+course.

    Idempoten — menghitung ulang dari state `UserProgress` seperti
    `sync_leaderboard`, sehingga aman dipanggil berulang dari setiap jalur
    mutasi poin. Badge diberi bila semua module course berstatus `finish`,
    dan dicabut (yang diberi sistem) bila tidak lagi lengkap. Badge manual
    (`awarded_by` mentor) tidak pernah disentuh di sini.

    Returns:
        list[UserBadge]: baris yang baru tercipta pada panggilan ini
        (kosong bila tidak ada perubahan) — sumber toast "badge baru".
    """
    new_badges = []
    total_modules = CourseModule.objects.filter(course=course).count()
    if not total_modules:
        return new_badges

    finished = UserProgress.objects.filter(
        user=user,
        module__course=course,
        status=UserProgress.ProgressStatus.FINISH,
    ).count()
    complete = finished == total_modules

    automatic = Badge.objects.filter(
        course=course, rule_type=Badge.RuleType.COURSE_COMPLETE
    )
    for badge in automatic:
        if complete:
            user_badge, created = UserBadge.objects.get_or_create(
                user=user,
                badge=badge,
                defaults={"awarded_by": "system"},
            )
            if created:
                new_badges.append(user_badge)
        else:
            UserBadge.objects.filter(
                user=user, badge=badge, awarded_by="system"
            ).delete()
    return new_badges

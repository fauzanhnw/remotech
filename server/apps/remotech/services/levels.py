"""Level on-the-fly dari akumulasi poin — tanpa tabel progres.

Level dihitung setiap kali dibutuhkan dari total poin lintas course
(sinkron leaderboard), sehingga tidak perlu disimpan maupun dimigrasi.
"""

# (ambang poin minimal, nama level) — urut menaik; tanpa ambang atas.
# Asumsi ~100 poin per modul bernilai (quiz/tugas), ~1.000 per course penuh.
LEVEL_TIERS: tuple[tuple[int, str], ...] = (
    (0, "Pemula"),
    (500, "Pelajar"),
    (1500, "Praktisi"),
    (4000, "Profesional"),
    (10000, "Ahli"),
    (25000, "Master"),
)


def level_for_points(total_points: int) -> tuple[int, str]:
    """(nomor level 1-based, nama level) untuk total poin tertentu."""
    level = 1
    title = LEVEL_TIERS[0][1]
    for index, (threshold, tier_title) in enumerate(LEVEL_TIERS, start=1):
        if total_points >= threshold:
            level = index
            title = tier_title
        else:
            break
    return level, title


def level_progress(
    total_points: int,
) -> tuple[int, str, str | None, int | None, int]:
    """Level + progres menuju level berikutnya (untuk progress bar UI).

    Mengembalikan `(level, title, next_title, points_to_next, percent)`.
    Di level maksimal, `next_title`/`points_to_next` None dan `percent` 100.
    `percent` dibulatkan ke int agar frontend tidak perlu tahu threshold.
    """
    level, title = level_for_points(total_points)
    if level >= len(LEVEL_TIERS):
        return level, title, None, None, 100

    current_threshold = LEVEL_TIERS[level - 1][0]
    next_threshold, next_title = LEVEL_TIERS[level]
    span = next_threshold - current_threshold
    percent = round((total_points - current_threshold) * 100 / span)
    return level, title, next_title, next_threshold - total_points, percent

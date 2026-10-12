from datetime import date

from app.services.membership_service import MembershipService


def test_previous_complete_month_handles_year_and_february_boundaries():
    assert MembershipService.previous_complete_month(date(2026, 1, 1)) == (
        date(2025, 12, 1),
        date(2025, 12, 31),
        date(2026, 1, 1),
    )
    assert MembershipService.previous_complete_month(date(2024, 3, 1)) == (
        date(2024, 2, 1),
        date(2024, 2, 29),
        date(2024, 3, 1),
    )
    assert MembershipService.previous_complete_month(date(2025, 3, 1)) == (
        date(2025, 2, 1),
        date(2025, 2, 28),
        date(2025, 3, 1),
    )

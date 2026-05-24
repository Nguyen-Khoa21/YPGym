def get_current_user_placeholder() -> dict[str, str]:
    """Temporary auth placeholder; replace with JWT validation on Day 10."""
    return {
        "id": "placeholder-user",
        "role": "guest",
    }

def normalize_username(raw_username):
    normalized = raw_username.strip().lower()
    return normalized.replace(" ", "_")


def is_valid_username(username):
    """Return True for usernames like 'alice', 'user_123', or 'abc_123'.

    Valid usernames are 3-20 characters and contain only lowercase ASCII letters, digits, or underscores.
    Invalid examples: 'ab' is too short, 'very_long_username_123' is too long, 'user-name' contains a hyphen, and 'ABC' contains uppercase letters.
    """
    # TODO: implement validation
    pass


def create_user_profile(raw_username):
    username = normalize_username(raw_username)
    if not is_valid_username(username):
        raise ValueError("username must be 3-20 characters and contain only letters, digits, or underscores")
    return {
        "username": username,
        "display_name": username.replace("_", " ").title(),
    }


if __name__ == "__main__":
    print(create_user_profile("  Alice_Example  "))

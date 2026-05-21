def normalize_username(raw_username):
    return username.strip().lower()


def create_user_profile(raw_username):
    normalized_username = normalize_username(raw_username)
    return {
        "username": normalized_username,
        "display_name": normalized_username.replace("_", " ").title(),
    }


if __name__ == "__main__":
    print(create_user_profile("  Alice_Example  "))

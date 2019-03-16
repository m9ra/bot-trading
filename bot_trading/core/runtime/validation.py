import re


def validate_email(username):
    if not re.match("[^@]+@[^@]+\.[^@]+", username):
        raise ValueError(f"Username must be an email but {username} was given")

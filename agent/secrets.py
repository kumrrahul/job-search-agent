import os

from dotenv import load_dotenv


load_dotenv()


def get(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(
            f"Missing required env var: {key}\n"
            "Add it to your .env file."
        )
    return val


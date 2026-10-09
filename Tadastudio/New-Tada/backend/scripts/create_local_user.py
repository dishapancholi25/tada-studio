"""Bootstrap a local-auth user. Run once to create your first login.

Usage (PowerShell):
    &"./venv/Scripts/python.exe" backend/scripts/create_local_user.py user@example.com MyP@ssw0rd
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so `import backend.*` works
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.models.auth.local_user import LocalUser  # noqa: E402,F401  (registers model)
from backend.services.auth.local_auth import create_local_user  # noqa: E402
from backend.services.database import Base, get_engine  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: create_local_user.py <email> <password>")
        sys.exit(1)

    # Make sure the local_users table exists
    Base.metadata.create_all(bind=get_engine(), tables=[LocalUser.__table__])

    email, password = sys.argv[1], sys.argv[2]
    user = create_local_user(email, password)
    print(f"Created local user: {user.email} (id={user.id})")


if __name__ == "__main__":
    main()

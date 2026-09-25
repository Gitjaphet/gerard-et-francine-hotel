import argparse
import asyncio
from datetime import UTC, datetime
from getpass import getpass

from app.core.roles import UserRole
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.repositories.login_attempt import LoginAttemptRepository
from app.repositories.user import UserRepository
from app.services.auth import LOCKOUT_WINDOW

MIN_PASSWORD_LENGTH = 12


def ask_password(email: str) -> str:
    password = getpass("Mot de passe : ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
    if email.lower() in password.lower():
        raise SystemExit("Le mot de passe ne doit pas contenir l'adresse email.")
    if password != getpass("Confirmation : "):
        raise SystemExit("Les mots de passe ne correspondent pas.")
    return password


async def create_user(email: str, full_name: str, role: UserRole) -> None:
    password = ask_password(email)
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        if await repo.get_by_email(email):
            raise SystemExit(f"Un compte existe déjà pour {email}.")
        await repo.add(
            User(
                email=email,
                full_name=full_name,
                role=role,
                hashed_password=hash_password(password),
            )
        )
        await db.commit()
    await engine.dispose()
    print(f"Compte {role.value} créé : {email}")


async def reset_password(email: str) -> None:
    password = ask_password(email)
    async with AsyncSessionLocal() as db:
        user = await UserRepository(db).get_by_email(email)
        if user is None:
            raise SystemExit(f"Aucun compte pour {email}.")
        user.hashed_password = hash_password(password)
        await db.commit()
    await engine.dispose()
    print(f"Mot de passe mis à jour : {email}")


async def unlock_user(email: str) -> None:
    since = datetime.now(UTC) - LOCKOUT_WINDOW
    async with AsyncSessionLocal() as db:
        removed = await LoginAttemptRepository(db).delete_failures_by_email(email, since)
        await db.commit()
    await engine.dispose()
    print(f"{removed} échec(s) récent(s) supprimé(s) pour {email}. Le compte est débloqué.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Administration de l'API Gérard et Francine")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-user", help="Créer un compte d'administration")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=UserRole.OWNER.value,
    )

    reset = commands.add_parser("reset-password", help="Changer le mot de passe d'un compte")
    reset.add_argument("--email", required=True)

    unlock = commands.add_parser("unlock-user", help="Débloquer un compte après trop d'échecs")
    unlock.add_argument("--email", required=True)

    args = parser.parse_args()
    email = args.email.strip().lower()
    if args.command == "create-user":
        asyncio.run(create_user(email, args.name.strip(), UserRole(args.role)))
    elif args.command == "reset-password":
        asyncio.run(reset_password(email))
    elif args.command == "unlock-user":
        asyncio.run(unlock_user(email))


if __name__ == "__main__":
    main()

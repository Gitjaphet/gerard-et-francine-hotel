import argparse
import asyncio
from getpass import getpass

from app.core.roles import UserRole
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.repositories.user import UserRepository

MIN_PASSWORD_LENGTH = 12


async def create_user(email: str, full_name: str, role: UserRole) -> None:
    password = getpass("Mot de passe : ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
    if password != getpass("Confirmation : "):
        raise SystemExit("Les mots de passe ne correspondent pas.")

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

    args = parser.parse_args()
    if args.command == "create-user":
        asyncio.run(create_user(args.email.strip().lower(), args.name.strip(), UserRole(args.role)))


if __name__ == "__main__":
    main()

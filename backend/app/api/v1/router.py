from fastapi import APIRouter

from app.api.deps import OwnerOnly
from app.api.v1 import auth, hotel, hotel_public, social_links

api_router = APIRouter(prefix="/api/v1")

# --- Public -------------------------------------------------------------------
api_router.include_router(auth.router)
api_router.include_router(hotel_public.router)

# --- Admin : propriétaire uniquement ------------------------------------------
api_router.include_router(hotel.router, dependencies=[OwnerOnly])
api_router.include_router(social_links.router, dependencies=[OwnerOnly])

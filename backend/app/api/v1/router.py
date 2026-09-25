from fastapi import APIRouter

from app.api.deps import OwnerOnly
from app.api.v1 import (
    amenities,
    auth,
    hotel,
    hotel_public,
    media,
    room_types,
    rooms_public,
    seasons,
    social_links,
)

api_router = APIRouter(prefix="/api/v1")

# --- Public -------------------------------------------------------------------
api_router.include_router(auth.router)
api_router.include_router(hotel_public.router)
api_router.include_router(rooms_public.router)

# --- Admin : propriétaire uniquement ------------------------------------------
api_router.include_router(hotel.router, dependencies=[OwnerOnly])
api_router.include_router(social_links.router, dependencies=[OwnerOnly])
api_router.include_router(amenities.router, dependencies=[OwnerOnly])
api_router.include_router(room_types.router, dependencies=[OwnerOnly])
api_router.include_router(media.router, dependencies=[OwnerOnly])
api_router.include_router(seasons.router, dependencies=[OwnerOnly])

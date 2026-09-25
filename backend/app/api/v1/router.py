from fastapi import APIRouter

from app.api.v1 import hotel, social_links

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(hotel.router)
api_router.include_router(social_links.router)

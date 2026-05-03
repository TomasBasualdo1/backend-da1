from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.usuarios import router as usuarios_router
from app.api.subastas import router as subastas_router
from app.api.articulos import router as articulos_router
from app.api.notificaciones import router as notificaciones_router
from app.api.admin import router as admin_router
from app.api.uploads import router as uploads_router
from app.api.paises import router as paises_router

router = APIRouter()

router.include_router(auth_router, tags=["Autenticacion"])
router.include_router(usuarios_router, tags=["Perfil"])
router.include_router(subastas_router, tags=["Subastas"])
router.include_router(articulos_router, tags=["Subastas"])
router.include_router(notificaciones_router, tags=["Notificaciones"])
router.include_router(admin_router, tags=["Administracion"])
router.include_router(uploads_router, tags=["Uploads"])
router.include_router(paises_router, tags=["Paises"])

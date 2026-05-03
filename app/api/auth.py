from fastapi import APIRouter

router = APIRouter(prefix="/auth")


@router.post("/registro/paso1", status_code=201)
async def registro_paso1():
    pass


@router.post("/registro/paso2", status_code=201)
async def registro_paso2():
    pass


@router.post("/login")
async def login():
    pass


@router.post("/verify-email")
async def verify_email():
    pass


@router.post("/forgot-password")
async def forgot_password():
    pass


@router.post("/reset-password")
async def reset_password():
    pass

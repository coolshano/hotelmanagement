from fastapi import APIRouter


router = APIRouter()


@router.post("/login")
def login():
    return {
        "access_token":"jwt-token",
        "token_type":"bearer"
    }


@router.post("/logout")
def logout():
    return {
        "message":"Logged out"
    }


@router.post("/refresh")
def refresh_token():
    return {
        "access_token":"new-token"
    }
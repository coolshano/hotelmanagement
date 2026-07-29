from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def payments():

    return []


@router.post("/")
def create_payment():

    return {
        "message":"Payment created"
    }


@router.get("/{payment_id}")
def get_payment(payment_id:int):

    return {
        "id":payment_id
    }
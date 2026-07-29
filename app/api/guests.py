from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def list_guests():
    return []


@router.post("/")
def create_guest():

    return {
        "message":"Guest created"
    }


@router.get("/{guest_id}")
def get_guest(guest_id:int):

    return {
        "id":guest_id
    }


@router.put("/{guest_id}")
def update_guest(guest_id:int):

    return {
        "message":"Updated"
    }


@router.delete("/{guest_id}")
def delete_guest(guest_id:int):

    return {
        "message":"Deleted"
    }
from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def list_rooms():

    return []


@router.get("/available")
def available_rooms():

    return []


@router.post("/")
def create_room():

    return {
        "message":"Room created"
    }


@router.put("/{room_id}")
def update_room(room_id:int):

    return {
        "message":"Updated"
    }


@router.delete("/{room_id}")
def delete_room(room_id:int):

    return {
        "message":"Deleted"
    }
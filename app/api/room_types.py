from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def get_room_types():
    return []


@router.post("/")
def create_room_type():

    return {
        "message":"Room type created"
    }


@router.put("/{id}")
def update_room_type(id:int):

    return {
        "message":"Updated"
    }


@router.delete("/{id}")
def delete_room_type(id:int):

    return {
        "message":"Deleted"
    }
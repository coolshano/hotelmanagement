from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def get_users():
    return []


@router.get("/{user_id}")
def get_user(user_id:int):

    return {
        "id":user_id
    }


@router.post("/")
def create_user():

    return {
        "message":"User created"
    }


@router.put("/{user_id}")
def update_user(user_id:int):

    return {
        "message":"User updated"
    }


@router.delete("/{user_id}")
def delete_user(user_id:int):

    return {
        "message":"User deleted"
    }
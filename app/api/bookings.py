from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def list_bookings():

    return []


@router.post("/")
def create_booking():

    return {
        "message":"Booking created"
    }


@router.get("/{booking_id}")
def get_booking(booking_id:int):

    return {
        "id":booking_id
    }


@router.put("/{booking_id}")
def update_booking(booking_id:int):

    return {
        "message":"Updated"
    }


@router.delete("/{booking_id}")
def cancel_booking(booking_id:int):

    return {
        "message":"Cancelled"
    }
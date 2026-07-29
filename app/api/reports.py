from fastapi import APIRouter


router = APIRouter()


@router.get("/occupancy")
def occupancy():

    return {
        "occupied":50,
        "available":20
    }


@router.get("/revenue")
def revenue():

    return {
        "monthly_revenue":10000
    }


@router.get("/bookings")
def booking_report():

    return []
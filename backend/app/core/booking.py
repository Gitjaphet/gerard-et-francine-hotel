from enum import StrEnum


class BookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class BookingWarning(StrEnum):
    OVER_CAPACITY = "over_capacity"
    MIN_STAY_NOT_MET = "min_stay_not_met"
    PRICE_UNAVAILABLE = "price_unavailable"

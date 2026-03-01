"""
SQLAlchemy ORM models. All use mapped_column and Mapped (2.0 style).
"""
from relayroute.models.base import Base
from relayroute.models.city import City
from relayroute.models.dropoff import DropoffPoint
from relayroute.models.order import Order
from relayroute.models.partner import Partner
from relayroute.models.restaurant import Restaurant
from relayroute.models.task import TaskEvent
from relayroute.models.zone import Zone

__all__ = [
    "Base",
    "City",
    "Zone",
    "Restaurant",
    "DropoffPoint",
    "Partner",
    "Order",
    "TaskEvent",
]

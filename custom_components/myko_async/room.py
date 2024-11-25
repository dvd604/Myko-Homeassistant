__all__ = [
    "HubSpaceRoom",
    "get_hs_room",
]
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .device import HubSpaceDevice

logger = logging.getLogger(__name__)


@dataclass
class HubSpaceRoom:
    id: str
    friendly_name: str
    children: Optional[list[HubSpaceDevice]] = field(default_factory=list)


def get_hs_room(
    hs_room: dict[str, Any], children: list[HubSpaceDevice] = None
) -> HubSpaceRoom:
    """Convert the HubSpace device definition into a HubSpaceDevice"""
    room_dict = {
        "id": hs_room.get("id"),
        "friendly_name": hs_room.get("friendlyName"),
        "children": children,
    }
    return HubSpaceRoom(**room_dict)

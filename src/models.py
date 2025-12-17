from dataclasses import dataclass
from typing import Optional

@dataclass
class Memory:
    url: str
    date: str
    type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

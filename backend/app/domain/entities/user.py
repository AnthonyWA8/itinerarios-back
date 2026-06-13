from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    name: str
    email: str
    password_hash: str
    created_at: datetime

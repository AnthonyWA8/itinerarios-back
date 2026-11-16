from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Optional


@dataclass
class GeoPoint:
    latitude: float
    longitude: float


@dataclass
class PlaceResult:
    """Lugar real devuelto por un proveedor de mapas."""
    name: str
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    url: Optional[str]
    rating: Optional[float]
    source: str


class PlacesError(Exception):
    """Fallo al consultar el proveedor de lugares."""


class PlacesSession(ABC):
    """Sesión abierta con un proveedor de lugares (permite varias consultas seguidas)."""

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        limit: int = 3,
        near: Optional[GeoPoint] = None,
        radius_m: Optional[int] = None,
    ) -> list[PlaceResult]:
        """Busca lugares reales por texto, opcionalmente cerca de un punto."""
        ...


class PlacesService(ABC):
    """Puerto del dominio: acceso a datos reales de lugares (mapas)."""

    source: str

    @abstractmethod
    def session(self) -> AbstractAsyncContextManager[PlacesSession]:
        """Abre una sesión con el proveedor para hacer una o varias búsquedas."""
        ...

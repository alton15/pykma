"""기상청 단기예보 API Python SDK."""

from .client import KMA
from .codes import Amount, Precipitation, Sky
from .errors import AuthError, KMAError, QuotaError, RequestError, ResponseError
from .grid import Grid, to_grid, to_latlon
from .models import Forecast, Observation

__version__ = "0.1.0"

__all__ = [
    "KMA",
    "Amount",
    "AuthError",
    "Forecast",
    "Grid",
    "KMAError",
    "Observation",
    "Precipitation",
    "QuotaError",
    "RequestError",
    "ResponseError",
    "Sky",
    "__version__",
    "to_grid",
    "to_latlon",
]

"""Provider package initialisation.

This package defines abstract provider interfaces (via ``Protocol``) and deterministic
mock implementations that expose the same contracts.  The rest of the backend
(geometry, drift, AIS, attribution) imports data through these providers, keeping
the core algorithms independent of any external service.
"""

# Export symbols for convenient import
from .satellite import SatelliteProvider, MockSatelliteProvider, SatelliteMetadata
from .weather import WeatherProvider, MockWeatherProvider, WindData
from .currents import CurrentsProvider, MockCurrentsProvider, CurrentData
from .ais_provider import AISProvider, MockAISProvider, AISRecord

__all__ = [
    "SatelliteProvider",
    "MockSatelliteProvider",
    "SatelliteMetadata",
    "WeatherProvider",
    "MockWeatherProvider",
    "WindData",
    "CurrentsProvider",
    "MockCurrentsProvider",
    "CurrentData",
    "AISProvider",
    "MockAISProvider",
    "AISRecord",
]

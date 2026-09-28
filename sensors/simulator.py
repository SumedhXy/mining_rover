from __future__ import annotations

import logging
import os
import sys

if __package__ in (None, ""):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from sensors.sensor_service import SensorService
from sensors.sources.simulator_source import SimulatorSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("sensor_simulator")


def main() -> None:
    logger.info("Sensor service started")
    logger.info("Source: simulator")

    service = SensorService(source=SimulatorSource(), logger=logger)
    service.start()

    for i in range(1, 4):
        reading = service.read()
        if reading is None:
            logger.error("No valid reading produced")
            continue

        print(f"Reading #{i}:")
        print(f"  Device ID:    {reading.device_id}")
        print(f"  Timestamp:    {reading.timestamp}")
        print(f"  Temperature:  {reading.temperature_c:.1f} °C")
        print(f"  Humidity:     {reading.humidity_percent:.1f} %")
        print(f"  Pressure:     {reading.pressure_hpa:.1f} hPa")
        print(f"  Methane:      {reading.methane:.3f} (MQ-4)")
        print(f"  Air Quality:  {reading.air_quality:.3f} (MQ-135)")
        print(f"  Source:       {reading.source}")
        print()

    service.stop()


if __name__ == "__main__":
    main()

__all__ = ["SimulatorSource", "main"]

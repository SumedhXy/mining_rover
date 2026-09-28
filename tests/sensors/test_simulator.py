from sensors.sources.simulator_source import SimulatorSource


def test_simulator_generates_valid_readings():
    source = SimulatorSource()

    for _ in range(10):
        reading = source.read()
        assert -40 <= reading.temperature <= 100
        assert 0 <= reading.humidity <= 100
        assert 0 <= reading.gas <= 1
        assert 0 <= reading.smoke <= 1


def test_simulator_can_produce_hazard_scenarios():
    source = SimulatorSource(scenario="gas_hazard")
    reading = source.read()

    assert reading.gas >= 0.7
    assert reading.temperature < 60

    source.set_scenario("smoke_hazard")
    smoke_reading = source.read()
    assert smoke_reading.smoke >= 0.7

from mosaik.exceptions import SimulationError


def test_simulation_error():
    exc = SimulationError('onoes')
    assert str(exc) == 'onoes'

    # Without a . at the end
    orig = ConnectionError(104, 'Connection reset by peer')
    exc = SimulationError('onoes', orig)
    assert str(exc) == '[Errno 104] Connection reset by peer: onoes'

    # With a . at the end
    orig = ConnectionError(104, 'Connection reset by peer.')
    exc = SimulationError('onoes', orig)
    assert str(exc) == '[Errno 104] Connection reset by peer: onoes'

from mesh_gate import _catastrophic_fragmentation_reason


def test_monja_shattered_surface_is_rejected():
    reason = _catastrophic_fragmentation_reason(1781, 0.012569)
    assert reason == "catastrophic_fragmentation:components=1781,largest=0.013"


def test_many_accessories_are_not_rejected_when_body_is_coherent():
    assert _catastrophic_fragmentation_reason(1400, 0.18) is None


def test_moderate_fragmentation_remains_telemetry_only():
    assert _catastrophic_fragmentation_reason(300, 0.02) is None

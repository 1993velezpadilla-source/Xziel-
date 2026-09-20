#include "xziel/acoustics.hpp"

#include <cassert>

int main() {
    xziel::AcousticGraph graph;

    assert(graph.addRoom({
        .id = 1,
        .preset = xziel::ReverbPreset::ConcreteRoom,
        .reverbAmount = 0.35f,
        .damping = 0.45f,
        .occlusionAbsorption = 0.55f,
    }));

    assert(graph.addRoom({
        .id = 2,
        .preset = xziel::ReverbPreset::Hall,
        .reverbAmount = 0.62f,
        .damping = 0.35f,
        .occlusionAbsorption = 0.42f,
    }));

    assert(graph.addRoom({
        .id = 3,
        .preset = xziel::ReverbPreset::Exterior,
        .reverbAmount = 0.12f,
        .damping = 0.20f,
        .occlusionAbsorption = 0.15f,
    }));

    assert(graph.addPortal({
        .id = 10,
        .roomA = 1,
        .roomB = 2,
        .openness = 1.0f,
        .absorption = 0.10f,
    }));

    assert(graph.addPortal({
        .id = 11,
        .roomA = 2,
        .roomB = 3,
        .openness = 0.5f,
        .absorption = 0.25f,
    }));

    auto result = graph.query({
        .sourceRoom = 3,
        .listenerRoom = 1,
        .directDistanceMeters = 12.0f,
        .sourceImportance = 1.0f,
    });

    assert(result.connected);
    assert(result.portalHops == 2);
    assert(result.transmission > 0.0f);
    assert(result.transmission < 1.0f);
    assert(result.occlusion > 0.0f);
    assert(result.lowPassHz < 20000.0f);

    const float openTransmission =
        result.transmission;

    assert(graph.setPortalOpenness(11, 0.05f));

    result = graph.query({
        .sourceRoom = 3,
        .listenerRoom = 1,
        .directDistanceMeters = 12.0f,
    });

    assert(result.connected);
    assert(result.transmission < openTransmission);
    assert(result.occlusion > 0.5f);

    assert(graph.setPortalOpenness(11, 0.0f));

    result = graph.query({
        .sourceRoom = 3,
        .listenerRoom = 1,
        .directDistanceMeters = 12.0f,
    });

    assert(!result.connected);
    assert(result.occlusion == 1.0f);

    return 0;
}

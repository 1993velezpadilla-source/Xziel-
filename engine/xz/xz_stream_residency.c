#include "xz_stream_residency.h"

#include <string.h>

static unsigned int XzTierBaseCapacity(
    XzDeviceTier tier)
{
    switch (tier) {
    case XZ_DEVICE_ULTRA: return 128u;
    case XZ_DEVICE_HIGH:  return 112u;
    case XZ_DEVICE_MID:   return 96u;
    case XZ_DEVICE_LOW:   return 72u;
    case XZ_DEVICE_COMPAT:
    default:
        return 56u;
    }
}

static unsigned int XzScaledCapacity(
    XzDeviceTier tier,
    float aggression)
{
    unsigned int base =
        XzTierBaseCapacity(tier);
    unsigned int value;

    if (aggression < 0.25f)
        aggression = 0.25f;
    if (aggression > 1.25f)
        aggression = 1.25f;

    value = (unsigned int)(
        (float)base * aggression + 0.5f);

    if (value < 16u)
        value = 16u;
    if (value > XZ_RESIDENCY_MAX_SLOTS)
        value = XZ_RESIDENCY_MAX_SLOTS;

    return value;
}

static int XzFindHash(
    const XzStreamResidency *state,
    uint32_t hash)
{
    unsigned int i;

    for (i = 0u; i < XZ_RESIDENCY_MAX_SLOTS; ++i) {
        if (state->slots[i].resident &&
            state->slots[i].asset_hash == hash)
            return (int)i;
    }

    return -1;
}

static int XzFindFree(
    const XzStreamResidency *state)
{
    unsigned int i;

    for (i = 0u; i < XZ_RESIDENCY_MAX_SLOTS; ++i) {
        if (!state->slots[i].resident)
            return (int)i;
    }

    return -1;
}

static int XzFindEvictionCandidate(
    const XzStreamResidency *state,
    uint64_t generation)
{
    int best = -1;
    unsigned int i;

    for (i = 0u; i < XZ_RESIDENCY_MAX_SLOTS; ++i) {
        const XzResidencySlot *slot =
            &state->slots[i];

        if (!slot->resident)
            continue;

        /* Never evict something touched by this plan update. */
        if (slot->last_seen_generation == generation)
            continue;

        if (best < 0) {
            best = (int)i;
            continue;
        }

        if (slot->priority <
                state->slots[best].priority ||
            (slot->priority ==
                 state->slots[best].priority &&
             slot->last_seen_generation <
                 state->slots[best].last_seen_generation))
            best = (int)i;
    }

    return best;
}

static void XzTrimToCapacity(
    XzStreamResidency *state,
    uint64_t generation)
{
    while (state->resident_count > state->capacity) {
        int candidate =
            XzFindEvictionCandidate(
                state, generation);

        if (candidate < 0)
            break;

        memset(
            &state->slots[candidate],
            0,
            sizeof(state->slots[candidate]));

        state->resident_count--;
        state->evictions++;
    }
}

void XzStreamResidency_Init(
    XzStreamResidency *state)
{
    if (!state)
        return;

    memset(state, 0, sizeof(*state));
    state->capacity =
        XzTierBaseCapacity(XZ_DEVICE_COMPAT);
    state->last_aggression = 1.0f;
}

void XzStreamResidency_Update(
    XzStreamResidency *state,
    const XzRenderPlan *plan,
    XzDeviceTier tier,
    const XzGovernorRecommendation *recommendation)
{
    unsigned int i;
    float aggression = 1.0f;
    uint32_t seen[XZ_RENDER_MAX_PACKETS];
    unsigned int seen_count = 0u;

    if (!state || !plan)
        return;

    if (recommendation)
        aggression =
            recommendation->streaming_aggression;

    state->capacity =
        XzScaledCapacity(tier, aggression);
    state->last_aggression = aggression;
    state->last_requested_unique = 0u;
    state->last_admitted_unique = 0u;
    state->updates++;

    for (i = 0u; i < plan->packet_count; ++i) {
        const XzRenderPacket *packet =
            &plan->packets[i];
        unsigned int j;
        int duplicate = 0;
        int slot_index;

        if (packet->asset_hash == 0u)
            continue;

        for (j = 0u; j < seen_count; ++j) {
            if (seen[j] == packet->asset_hash) {
                duplicate = 1;
                break;
            }
        }

        if (duplicate)
            continue;

        seen[seen_count++] = packet->asset_hash;
        state->last_requested_unique++;

        slot_index =
            XzFindHash(
                state,
                packet->asset_hash);

        if (slot_index >= 0) {
            XzResidencySlot *slot =
                &state->slots[slot_index];

            slot->last_seen_generation =
                plan->generation;
            if (packet->priority_class > slot->priority)
                slot->priority =
                    packet->priority_class;
            if (packet->lod < slot->lod)
                slot->lod = packet->lod;

            state->hits++;
            state->last_admitted_unique++;
            if (packet->priority_class >= 2u)
                state->protected_keeps++;
            continue;
        }

        if (state->resident_count >= state->capacity) {
            int evict =
                XzFindEvictionCandidate(
                    state,
                    plan->generation);

            if (evict >= 0) {
                memset(
                    &state->slots[evict],
                    0,
                    sizeof(state->slots[evict]));
                state->resident_count--;
                state->evictions++;
            }
        }

        slot_index = XzFindFree(state);
        if (slot_index < 0 ||
            state->resident_count >= state->capacity) {
            state->misses++;
            continue;
        }

        state->slots[slot_index].asset_hash =
            packet->asset_hash;
        state->slots[slot_index].last_seen_generation =
            plan->generation;
        state->slots[slot_index].priority =
            packet->priority_class;
        state->slots[slot_index].lod =
            packet->lod;
        state->slots[slot_index].resident = 1u;

        state->resident_count++;
        state->loads++;
        state->last_admitted_unique++;

        if (state->resident_count >
            state->high_water_count)
            state->high_water_count =
                state->resident_count;
    }

    XzTrimToCapacity(
        state,
        plan->generation);
}

int XzStreamResidency_SelfTest(void)
{
    XzStreamResidency state;
    XzRenderPlan plan;
    XzGovernorRecommendation rec;
    unsigned int i;

    XzStreamResidency_Init(&state);
    memset(&plan, 0, sizeof(plan));
    memset(&rec, 0, sizeof(rec));

    rec.streaming_aggression = 0.90f;
    plan.generation = 1u;
    plan.packet_count = 8u;

    for (i = 0u; i < plan.packet_count; ++i) {
        plan.packets[i].asset_hash = 100u + i;
        plan.packets[i].priority_class =
            i < 2u ? 3u : 1u;
        plan.packets[i].lod =
            i < 2u
                ? XZ_RENDER_LOD_NEAR
                : XZ_RENDER_LOD_MID;
    }

    XzStreamResidency_Update(
        &state,
        &plan,
        XZ_DEVICE_COMPAT,
        &rec);

    if (state.loads != 8u ||
        state.resident_count != 8u ||
        state.last_requested_unique != 8u ||
        state.last_admitted_unique != 8u)
        return 0;

    plan.generation = 2u;
    XzStreamResidency_Update(
        &state,
        &plan,
        XZ_DEVICE_COMPAT,
        &rec);

    if (state.hits != 8u ||
        state.loads != 8u)
        return 0;

    return 1;
}

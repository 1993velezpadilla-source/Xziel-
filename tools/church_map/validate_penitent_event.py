import json
import random
from pathlib import Path

CONFIG = Path("tools/church_map/penitent_event_config.json")
cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

assert cfg["id"] == "event_penitent_nun"
assert cfg["fullEventsPerMatch"] == 1
assert cfg["reward"]["mainQuestRequired"] is False
assert cfg["roundAccounting"]["prayingCountsTowardRoundPopulation"] is False
assert cfg["spatialAudio"]["placeholder"]["license"] == "CC0"
assert cfg["wrathHunt"]["canOneShotFullHealthWithoutTelegraph"] is False
assert cfg["wrathHunt"]["damageTeleportInPlayerView"] is False

weights = cfg["seededOutcomeWeights"]
assert abs(sum(weights.values()) - 1.0) < 1e-9, weights
space = cfg["personalSpaceReaction"]
assert abs(sum(space.values()) - 1.0) < 1e-9, space

sm = cfg["stateMachine"]
states = set(sm["states"])
assert sm["initial"] in states
assert "COMPLETE" in states
for src, edges in sm["transitions"].items():
    assert src in states, src
    for event, dst in edges.items():
        assert dst in states, (src, event, dst)

# Every non-terminal state in the authored graph must have a route to COMPLETE.
def reaches_complete(start):
    seen = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        if cur == "COMPLETE":
            return True
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(sm["transitions"].get(cur, {}).values())
    return False

for state in states:
    assert reaches_complete(state), f"No COMPLETE path from {state}"

# Determinism check: same match seed must choose the same authored family.
names = list(weights)
cumulative = []
acc = 0.0
for n in names:
    acc += weights[n]
    cumulative.append((acc, n))

def outcome(seed):
    r = random.Random(seed).random()
    for threshold, name in cumulative:
        if r <= threshold:
            return name
    return names[-1]

for seed in range(500):
    assert outcome(seed) == outcome(seed)

# Broad distribution sanity check, not a balance test.
counts = {k: 0 for k in names}
for seed in range(10000):
    counts[outcome(seed)] += 1
for k, expected in weights.items():
    observed = counts[k] / 10000.0
    assert abs(observed - expected) < 0.025, (k, observed, expected)

print("PENITENT_CONFIG_OK")
print("OUTCOME_COUNTS", counts)
print("STATES", len(states))

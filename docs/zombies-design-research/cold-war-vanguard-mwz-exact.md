# Cold War, Vanguard & MWZ — Exact Progression Research

Updated: 2026-09-20

Purpose: close the remaining structural gap between the classic round-based era and the BO6/BO7 research already stored in this corpus. These notes preserve **dependency order, failure/retry behavior, persistence, solo/co-op translation and meta-progression**.

This is design research, not copied walkthrough text. Randomized codes and live-match puzzle inputs must always be read from the current game state.

---

# BLACK OPS COLD WAR

## Die Maschine — Seal the Deal

### Required order

1. **Open the facility.**
   - Buy the route from the Yard through Nacht into the underground complex.
   - Reach the Particle Accelerator.

2. **Restore power.**
   - Turn on main power.
   - Activate the two accelerator terminals.
   - Enter the Dark Aether portal that appears.

3. **Forge Pack-a-Punch.**
   - In the Dark Aether, enter the Aether Tunnel.
   - Recover the Machine Part.
   - Return it to the accelerator.
   - Forge Pack-a-Punch.

4. **Obtain the D.I.E. Shockwave.**
   - Kill a Megaton.
   - Take its keycard.
   - Use the Weapons Lab terminal to obtain the D.I.E. Remote.
   - Activate the Nacht suction/trap system.
   - Feed zombies into it.
   - Discharge it to blow open the sealed D.I.E. room.
   - Take the D.I.E. Shockwave.

5. **Unlock all four D.I.E. elemental variants.**
   - Nova-5.
   - Cryo-Emitter.
   - Electrobolt.
   - Thermophasic.
   - Each uses a different map interaction rather than one repeated recipe.

6. **Build the Aetherscope.**
   - Enter the Dark Aether.
   - Collect all three Aetherscope parts.
   - Assemble it at the workbench.

7. **Recover Vogel's Diary.**
   - Use the Aetherscope to reveal the required spectral state.
   - Take the diary in Medical Bay.

8. **Give the diary to the three Spectral Reflections.**
   - Interact with each spectral scene.
   - Let the dialogue/scene complete.
   - Use the recovered information at the computer.

9. **Charge the Medical Bay device.**
   - Fire the correct four D.I.E. elements into their matching ports.

10. **Recover the Decontamination Agent.**
    - Use the outdoor tank sequence.
    - Recover the agent from the tree route.
    - Carry it to the Medical Bay chamber.
    - While carrying it, movement options are intentionally restricted.

11. **Capture the Megaton halves.**
    - Split the required Megaton.
    - Force both halves into the chamber.
    - Complete the decontamination interaction.

12. **Commit to the finale.**
    - Take Orlov's family photo.
    - This is the point of no return; finish all shopping and armor prep first.

13. **Orlov defense + escape.**
    - Defend Orlov while he works through three terminal positions.
    - When the facility destabilizes, follow the safe route to the Pond.
    - Reach the helicopter before the approximately 90-second escape expires.

### Design observations

- The D.I.E. is a signature tool with four distinct interaction grammars.
- Dark Aether is a temporary world-state layer that recontextualizes familiar rooms.
- The final photo gives a physical, diegetic point-of-no-return object.
- The ending is not only a boss: it is **defense followed by timed escape**.

---

## Firebase Z — Maxis Potential

### Required order

1. **Reach Firebase Z.**
   - Open the Village route.
   - Use the rooftop teleporter.

2. **Restore power through three Aether Reactors.**
   - Mission Control.
   - Data Center.
   - Military Command.
   - Each reactor is a local defense event; kills must happen close enough to feed the collection units.

3. **Unlock normal progression.**
   - Pack-a-Punch is available back in the Village once power is restored.
   - Build/acquire the RAI K-84; its alternate fire matters later.

4. **Begin the Peck/Ravenov story chain.**
   - Speak with Ravenov.
   - Meet Peck.
   - Prepare the truth-serum delivery system.
   - Gas Peck through the ventilation interaction.

5. **Capture the three correct Mimic memories.**
   - Use Essence Traps.
   - Weaken the correct Mimics rather than killing them.
   - Capture and process their memories.
   - Only the three required identities count; incorrect memories are deliberate decoys.

6. **Recover the three Aetherium containers.**
   - Use the Aethermeter/Shovel progression.
   - Each container has a different behavioral puzzle.
   - The Open Lot container uses visual smoke feedback to distinguish real from false.
   - The RAI K-84 alt-fire is needed for the moving-container interaction.
   - Install one completed container at each reactor.

7. **Align the satellite.**
   - Use the Planning Office terminal.
   - Select the Requiem target, identified by the yellow question mark.
   - Ignore flag-marked decoy satellites.

8. **Enter the OPC.**
   - This is effectively the finale commit.
   - Finish armor/ammo/perk prep first.

9. **Defeat Orda.**
   - Prioritize the glowing mouth.
   - Avoid the lethal slam zone.
   - Clear specials when they block clean damage windows.

### Design observations

- Three reactors turn “power” into active combat rather than a switch.
- The Mimic phase is a disguised-target identification game.
- Containers deliberately use three different behaviors so “collect three things” does not become repetition.
- Assault Rounds create a second defensive loop that exists outside the Main Quest.

---

## Outbreak — Ravenov Implications

### World structure

Outbreak is not one fixed map. The base loop is:

1. enter a region at World Tier 1;
2. optionally complete side activities;
3. complete the region's primary objective;
4. reach the Beacon;
5. upgrade, Exfil or warp;
6. each warp raises World Tier and enemy pressure.

The first Main Quest becomes available at World Tier 3.

### Quest 1 — Ravenov Implications

1. **Find the unmarked radio at World Tier 3+.**
   - Activate it.
   - Clear the attack.
   - Listen/read the broadcast frequency.

2. **Tune the three nearby amplifiers.**
   - Match each to the main radio frequency.
   - Collect the Beacon Listening Device.

3. **Respond at the Beacon and warp.**

4. **In the next eligible non-Ruka region, search the monkey statues.**
   - Find the one associated with the painted M.
   - Shoot it.
   - Recover the Microfilm.

5. **Use the projector.**
   - Insert the Microfilm.
   - Play all required transmissions.
   - The next warp is forced to Ruka.

6. **Enter Ruka's missile silos and lift lockdown.**

7. **Obtain the silo launch keys.**
   - Trap the vent Aether Monkey with an Essence Trap.
   - Shoot Aetherium crystals and collect enough chunks to charge the canister.
   - Use the jellyfish/lift interaction for the suspended key route.
   - Trigger and kill the disguised Mimic HVT for the remaining key.

8. **Read the launch order.**
   - Each silo console shows two red lights and one green light.
   - The green light's position encodes that silo's place in the activation order.
   - The answer is randomized each match.

9. **Activate the launch consoles in order within the short window.**

10. **Start the shared ten-minute finale timer.**
    - The timer covers both surface traversal and the Legion fight.

11. **Defeat Legion.**
    - Break the glowing chest.
    - When Legion kneels, focus one exposed orb.
    - Repeat chest break → one orb until all three orbs are destroyed.

### Quest 1 design lesson

Open-world prep is optional, but the finale has a strict shared timer. This converts the player's earlier loot/route decisions into a meaningful readiness test.

---

## Outbreak — Operation Excision

1. **Reach World Tier 3+ in a region other than Sanatorium.**

2. **Find the red Aether rift.**
   - Enter it.
   - Chain through the airborne red rifts.
   - Missing the sequence normally means retrying in another eligible region.

3. **Collect the second Beacon Listening Device.**

4. **Respond at the Beacon.**
   - The next destination becomes nighttime Sanatorium.

5. **Clear the crashed-helicopter area and play the Omega recording.**

6. **Push the Aethereal Orb onto the rover.**
   - Weapon fire physically moves it.
   - This is a world-physics escort interaction rather than a normal pickup.

7. **Recover the bunny from the broken Mystery Box.**
   - Survive the spawned wave.
   - Carry it to the rover.

8. **Prepare before starting the rover.**
   - Starting it is the point of no return for this quest.

9. **Escort the rover.**
   - Stay inside its Neutralizer bubble.
   - Leaving the bubble causes escalating environmental damage.

10. **Reach Monument Walk and play the rooftop recording.**
    - This begins the final Exfil timer.

11. **Rush to East Gardens.**

12. **Kill Orda and all remaining hostiles.**
    - Normal enemies continue to spawn until Orda dies.

13. **Board the helicopter before time expires.**

### Quest 2 design lesson

This is a strong example of an **escort that changes the traversal rules**: the objective creates a moving safe zone rather than asking players to stand beside a slow NPC for no reason.

---

## Cold War — The Pact meta reward

After completing core Main Quests, the player can use the Ritual Site at Zoo.

Completion count maps to permanent starting weapon rarity:
- 2 core Main Quests → Uncommon.
- 4 → Rare.
- 6 → Epic.

The reward can be disabled again at the ritual site.

### Xziel lesson

Persistent power should be:
- earned;
- visible in-world;
- incremental;
- optional/toggleable.

---

## Mauer der Toten — Tin Man Heart

### Required order

1. **Reach the underground power room.**
2. **Kill Tempests for the two electrical fuses.**
3. **Install both fuses and restore power.**
4. **Unlock Pack-a-Punch at Checkpoint Charlie after the activation fight.**
5. **Build KLAUS.**
   - Recover the battery.
   - Recover the robotic hands.
   - Assemble him.
6. **Charge KLAUS with kills.**
7. **Upgrade KLAUS until he can perform the heavy world interactions required by the quest.**
8. **Obtain the CRBR-S from the Hotel Room 305 safe.**
   - The three-number safe code is randomized and must be read from the current match.
9. **Obtain the CRBR-S Blazer mod.**
10. **Use the Blazer to melt the Secret Lab wall.**
11. **Use KLAUS to finish opening the laboratory route.**
12. **Build/use the Hacking Helm and complete the satellite/computer interactions.**
13. **Stop the train and recover the warhead/story items.**
14. **Complete the uranium device steps.**
15. **After the second cleansed-uranium completion, prepare for the endgame.**
16. **Enter the Valentina fight.**
    - She moves through multiple Berlin locations rather than remaining in one static arena.
17. **Defeat Valentina through her repeated shield/damage phases.**
18. **KLAUS carries the warhead.**
19. **Escort KLAUS to the portal while clearing his route.**
20. **Trigger the ending.**

### Design observations

- KLAUS is combat ally + revive support + world key + escort subject.
- The boss uses the real map rather than a disconnected arena.
- Safe-code randomization is fair because all three numbers are exposed in the current match.

---

## Forsaken — Nowhere but Forwards

### Required order

1. **Survive the accelerated Staging Area rounds.**
   - Feed kills to the teleporter quickly.
   - Leaving restores normal pacing.

2. **Open Anytown / Observation Tower progression and Pack-a-Punch.**

3. **Build the Chrysalax.**
   - Tempered Crystal Heart.
   - Energetic Geode.
   - Polymorphic Crystal Core.
   - The weapon switches between melee/axe and firearm modes.

4. **Complete the story-objective chain around the Observation Tower and Containment Zone.**

5. **Collect the Aetherium Neutralizer components.**
   - Fuel Tank.
   - Monitoring Device.
   - Housing Unit.

6. **Complete the Fuel Processing lockdown.**
   - Solo uses a single interaction.
   - Co-op requires the team interaction in its co-op form.

7. **Use the Abomination/catalyzed-crystal interaction where required.**

8. **Assemble the Neutralizer.**

9. **Finish every optional preparation step before activating it.**
   - Activating the Neutralizer is the point of no return.

10. **Escort the Neutralizer down Main Street.**
    - Remain inside its protected zone.
    - Refuel it by breaking the required orange Dark Aether crystals.

11. **Enter the Forsaken encounter.**

12. **Charge Samantha's laser cannons by killing inside the glowing zones.**

13. **Use the cannons to strip the Forsaken's armor.**
    - shoulders;
    - lower torso;
    - head.

14. **Complete the scripted ending.**
    - The final team-down is narrative, not a failed run.

### Design observations

- The opening accelerates rounds intentionally instead of making players idle through low-pressure setup.
- The signature Wonder Weapon has two combat identities.
- The escort uses resource refueling and environmental hazard rather than pure escort speed.
- A scripted “loss of control” can be story punctuation if clearly communicated as success, not failure.

---

# VANGUARD

## Der Anfang — objective-hub model

Der Anfang is valuable as a structure study even though it does not use a classic hidden Main Quest.

### Session loop

1. Start in Fountain Square.
2. Choose one of the available red objective portals.
3. Complete the objective.
4. Return to the hub.
5. The round advances.
6. New sectors and systems open.
7. Enemy health/special pressure rises.
8. Repeat while following Krafft/Von List narrative beats.
9. Enter the Void when desired for round-based survival.
10. Exfil when ready.

### Objective families

- Blitz.
- Harvest.
- Transmit.
- Purge.
- Sacrifice.
- Void.

### Xziel lesson

A hub-and-mission structure can make Zombies feel like a run-based campaign without requiring a giant continuous quest script.

---

## Terra Maledicta

### Required order

1. **Clear portal objectives to open the Eastern Desert hub.**
2. **Open East Spring and West Spring.**
3. **Acquire a shovel.**
4. **Begin the Decimator Shield quest.**
5. **Complete the first rune path.**
6. **Complete the second rune path.**
7. **Use the Augmentor/Sacrifice objective systems where required.**
8. **Recover the four required crystals.**
9. **Build/claim the Decimator Shield.**
10. **Enter the Debris Field Void.**
11. **Use the Shield's charged slam to free the four trapped arms.**
12. **Recover the page of the Tome of Rituals.**
13. **Complete the story payoff.**

### Design observations

- The first real Vanguard story quest grows naturally out of the objective-hub structure.
- The Wonder Weapon is simultaneously shield, crowd-control tool and quest verb.
- There is no separate boss arena; the quest's climax is the Void objective itself.

---

## Shi No Numa Reborn

### Required order

1. **Open the swamp and restore normal round-based progression.**

2. **Start the Monolith ceremony.**
   - Read/solve the cipher state.
   - Trigger the blue-mist ritual sequence.

3. **Build the Wunderwaffe DG-2.**
   - Recover the barrel.
   - Recover all three vacuum tubes.
   - One tube route is tied to a later round/special-enemy condition, so the quest naturally spans multiple rounds.

4. **Complete the Monolith/soul progression.**

5. **Repair the shattered mirror.**
   - Enter the Zombie Blood/perception state.
   - Recover the required mirror fragments.

6. **Complete all four blue-orb routes.**
   - Each orb travels to a different map area.
   - Follow and protect/complete each route.

7. **Return to the central ceremony.**

8. **Trigger the final Echo of Saraxis lockdown.**
   - All players must be ready before the final interaction.
   - Solo uses the equivalent single-player trigger.

9. **Defeat the Echo of Saraxis.**

### Design observations

- Reborn demonstrates how an old survival layout can support a modern full quest without losing the original map identity.
- The quest repeatedly reuses the swamp's huts and paths rather than adding a detached puzzle room.
- Perception states such as Zombie Blood can expose information without requiring a separate UI.

---

## The Archon — There Archon Be Only One

### Required order

1. **Rebuild Pack-a-Punch.**
   - Recover both ghostly Pack-a-Punch parts.
   - Return them to the Temple.
   - Complete the soul defense.

2. **Enter the scripted Dark Aether transition.**
   - The forced team-down at the end of this segment is part of the story, not a wipe.

3. **Complete the three Trials in any order.**

### Trial of Mindfulness

4. Dig up the red orb near Merchant Road.
5. Memorize/execute the symbol sequences.
6. Start the formal trial.
7. Capture the marked runes without killing zombies.
8. If failed, retry on a later round.

### Trial of Resilience

9. Shoot the correct Dark Aether crystal.
10. Complete the three cursed-item carry challenges.
    - sprint is disabled while carrying them.
11. Claim the Decimator Shield.
12. Use its charged slam to destroy the three Syphoncores.
13. Carry their Demon Blood to the fountain.

### Trial of Sacrifice

14. Light the three torches.
15. Sacrifice a disposable Pack-a-Punched weapon.
    - the weapon is permanently lost.
16. Kill the resulting Uberkrieger.
17. Use Ring of Fire to charge the satellite obelisks with kills.

### Finale

18. Fully prepare.
19. Enter the portal beside Pack-a-Punch.
    - this is the point of no return.

20. **Kortifex phase 1**
    - expose and destroy the upper eye.

21. **Kortifex phase 2**
    - collect/transform the crystal shard.
    - crash a pillar into the Construct.
    - drop the shield.
    - destroy the second eye.

22. **Kortifex phase 3**
    - repeat the shard/pillar logic.
    - interrupt Kortifex's healing.
    - destroy the final eye.

### Design observations

- The three Trials can be completed in flexible order.
- Each Trial tests a different skill: memory/nonlethal control, constrained carrying/defense, and resource sacrifice/combat positioning.
- Permanently consuming a weapon is acceptable only because the game makes the sacrifice explicit.
- The boss remixes the trial mechanics rather than becoming pure DPS.

---

# MODERN WARFARE III — MWZ / OPERATION DEAD BOLT

MWZ should not be modeled as a classic round-based Easter Egg. Its design value is **persistent campaign progression across deployments**.

## Core deployment loop

1. Choose a Strike Team Operator.
2. Select one active Mission.
3. Choose insured weapon / Acquisitions / crafted items.
4. Infil into Urzikstan.
5. Spawn in the Low Threat outer region.
6. Complete Contracts and Activities for Essence/loot.
7. Upgrade weapon rarity and Pack-a-Punch level.
8. Move inward only when ready:
   - Low Threat;
   - Medium Threat;
   - High Threat.
9. Complete the selected Mission requirement.
10. Decide whether to continue farming/progressing or Exfil.
11. Successful Exfil preserves selected loot and progression resources.
12. Schematics permanently add craftable Acquisitions with cooldowns.

### Design lesson

This turns survival preparation itself into campaign progression. A failed deployment has real cost because carried gear is at risk.

---

## Acts I–III — campaign ladder

### Normal mission structure

1. Act begins at Tier 1.
2. Complete the missions within the current Tier.
3. Later Tiers unlock.
4. Missions deliberately teach mode systems:
   - Contracts;
   - ammo mods;
   - field upgrades;
   - Strongholds;
   - Warlords;
   - Aether Storm;
   - high-threat-zone play;
   - extracting schematics.
5. Finish all required Tier missions.
6. The Act's isolated Story Mission becomes available.

### Story Mission transition

7. Equip the Story Mission.
8. Infil into normal Urzikstan.
9. Prepare as much as necessary during the normal deployment.
10. Travel to the special red-smoke Story Exfil.
11. Board it.
12. Load into an isolated instance containing only your squad.
13. Complete the scripted mission.
14. The next Act becomes available after successful completion.

### Act finales

- **Act I — Extraction:** recover/exfil Dr. Jansen through the isolated story route.
- **Act II — Shepherd:** deploy to the Neutralizer Test Site and successfully test the Neutralizer.
- **Act III — Defeat Zakhaev:** assault Zakhaev's Stronghold, use the completed Neutralizer plan and complete the Orcus/final cleansing story encounter.

### Design observations

- Public-space gearing flows into private-story instances.
- Players can prepare inside the same run before crossing the story gate.
- Mission tiers function as an extended tutorial that becomes more demanding rather than front-loading a tutorial menu.

---

## Act IV — seasonal Dark Aether story chain

Act IV expanded over multiple seasons instead of using traditional mission tiers.

### Bad Signal

1. Activate the Bad Signal Story Mission.
2. Enter its Dark Aether portal.
3. Locate the four seals.
4. Activate one seal at a time.
5. Kill zombies inside each seal's zone until it breaks.
6. After all four are destroyed, move toward extraction.
7. Fight Gorm'gant.
8. Attack the exposed purple weak points while avoiding laser, slam, burrow and tracking-orb pressure.
9. Kill Gorm'gant.
10. Take the **Locked Diary** from the Reward Rift.
11. Exfil through the portal.

The Locked Diary becomes the first key for the first replayable Dark Aether portal.

### Countermeasures

1. Activate the Countermeasures story portal.
2. Enter the new Dark Aether area.
3. Locate/rescue the stranded Terminus force.
4. Escort the ACV through the zone.
5. Complete the story defense/objective chain.
6. During the mission, optional hidden obelisks can be completed under specific rules to expose later portal relics.
7. Finish the story mission.
8. Take the **Drum** from the Reward Rift.

Portal-unlock research from this mission includes:
- Tattered MMA Gloves → melee-condition challenge.
- Perforated Target → headshot-condition challenge.
- Pristine Mirror → match the requested ammo-mod element.
- Drum → already attuned from story completion.

Back in Urzikstan, the three non-Drum relics must be attuned through themed activities before being placed at the Nahr Bathhouse portal.

### Union

1. Complete/activate the Union story path.
2. Enter the Dark Aether story instance.
3. Complete its story encounter.
4. Earn the **Giraffe Toy**, the first key for the Old Town replayable portal.

The remaining Old Town relics are recovered in normal Urzikstan:
- Laptop — transform/kill the specified Terminus Sergeant interaction.
- Imaginary Friend Drawing — follow the environmental footprint clue to a bed.
- Science Journal — kill the required number of zombies in the Aether Storm.

Then:
5. Perform the associated Summoning/attunement events.
6. Upgrade the relics to their usable portal state.
7. Place the completed relic set at the Old Town portal.
8. Unlock that Rift permanently for future use.

### Ascension — final MWZ story mission

1. Equip Ascension.
2. Enter the portal in/near the Opal Palace High Threat area.
3. Meet Ravenov and Ava in the Dark Aether city.
4. Use Aetherium launch pads to traverse floating rooftops/islands.
5. Reach the first obelisk.
6. Collect the four nearby legacy relics.
7. Place them at the obelisk.
8. Kill zombies near Ava to charge the destruction event.
9. Move to the second obelisk.
10. Gather its four relics.
11. Begin its charge.
12. When the Entity scatters the relics, recover and replace them.
13. Finish charging Ava and destroy the second obelisk.
14. Traverse the floating train/vehicle/platform route toward the tower.
15. Use the final launch-pad chain to reach the Entity arena.

### Entity boss

16. Destroy the glowing orbs on the Entity.
17. Avoid its beam and tracking projectiles.
18. Follow it when it relocates between islands.
19. During later phases, kill zombies near Ava to charge her attack.
20. Use those windows to continue stripping the Entity.
21. Survive the fake-out/final phase.
22. Defeat the Entity.
23. Claim **Mr. Peeks** from the Reward Rift.
24. Exfil through Ava's portal.
25. The cinematic closes MWZ's story and Mr. Peeks becomes the first piece for the final replayable Rift.

---

# MWZ — replayable Dark Aether Rift architecture

This system is one of the most reusable ideas in the entire franchise.

## Generic portal unlock loop

1. Complete the related Story Mission.
2. Receive one guaranteed story relic.
3. Discover three additional relics through hidden normal-world interactions.
4. Some relics initially spawn in a lower/unattuned quality.
5. Perform a themed challenge for each relic.
6. Convert it to the attuned/gold state.
7. Bring the complete set to the portal.
8. Place each relic in its matching pedestal.
9. Survive the unlock event.
10. The portal becomes permanently available for that profile.

## Standard Rift run

11. Obtain/use the Rift entry condition.
12. Enter a separate timed Dark Aether instance.
13. Complete several contracts/objectives.
14. Loot high-tier rewards and Schematics.
15. Exfil before the instance expires.

## Elder Rift

16. Obtain an Elder Sigil from high-end content.
17. Use it at the portal.
18. Enter the harder version.
19. Complete the tighter/harder contract set.
20. Extract with rare/persistent rewards.

By MWIII Season 6, unlocked Dark Aether Rifts could be run without spending a Sigil during the celebration period, while permanent Schematics remained the long-term reward loop.

---

# What MWZ adds to the Xziel design vocabulary

## 1. Quest state across many matches

A quest item can be:
- found in one run;
- extracted;
- stored;
- upgraded in a later run;
- placed at a portal days later.

Engine implication:
our quest system needs both **MatchQuestState** and **PersistentQuestState**.

## 2. Public world → private finale

Players may:
- prepare in a shared region;
- cross a gate;
- enter an isolated story instance with only their squad.

This solves interference problems while preserving an open-world social space.

## 3. Persistent crafting knowledge

Schematics permanently teach the account how to craft an Acquisition after a cooldown.

Xziel adaptation:
- relic recipe;
- weapon blueprint;
- potion recipe;
- temporary companion summon;
- traversal consumable.

## 4. Failure with meaningful stakes

Because carried loot may be lost, extraction matters.

An original Xziel extraction mode could use:
- insured quest items;
- protected story relic slot;
- optional high-value backpack slots;
- permanent recipes;
- recoverable lost gear.

Do not allow one network disconnect to permanently erase a critical story artifact.

## 5. Seasonal portal expansion

MWZ shows how the same open world can accumulate new hidden quest layers:
- new Story Mission;
- new relic set;
- new portal;
- new repeatable instance;
- new schematics.

For Xziel, this is a strong model for post-launch map expansion without replacing the base world.

---

# Cross-era conclusions from Cold War → Vanguard → MWZ

This era adds several reusable concepts not emphasized in earlier round-based maps:

- objective-driven hub progression;
- open-region questing;
- explicit Exfil as a strategic choice;
- field-upgrade abilities used as puzzle verbs;
- companions that fight and manipulate the world;
- guided Main Quest structures that still allow secrets;
- permanent account rewards from story completion;
- public-session preparation followed by private story instances;
- quest objects that persist across separate matches;
- permanent portal unlocks;
- repeatable hard-mode instances;
- schematics/recipes as progression rewards;
- strict point-of-no-return gates before bosses/escorts;
- solo-safe translations of synchronized interactions.

The important Xziel principle is:

**A Zombies quest does not have to begin and end inside one uninterrupted round-based match.**

Our quest runtime should be capable of classic one-session Easter Eggs **and** persistent multi-session campaign arcs.

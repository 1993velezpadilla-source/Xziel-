# Modern Exact Quest Orders — BO6 / BO7

Updated: 2026-09-20

Purpose: preserve the **exact gameplay order and dependency logic** of the most recent round-based Zombies quests so Xziel design work can study concrete successful structures rather than vague summaries.

These are original normalized notes based on current walkthroughs. Randomized codes must always be read from the live match; never hard-code another player's solution.

---

# Black Ops 6 — Shattered Veil

## Main Quest dependency order

1. **Repair the Banquet Hall elevator.**
   - Recover the fuse from the Library.
   - Recover the circuit board from the Director's Quarters.
   - Install both parts from behind the elevator and call it.

2. **Reach Pack-a-Punch.**
   - Use the elevator shaft rappel.
   - Descend to the Mainframe Chamber.
   - Pack-a-Punch becomes available.

3. **Start the Ray Gun Mark II chain.**
   - From round 10 onward, kill the lab-technician zombie.
   - Pick up the gold floppy disk.
   - Insert it into the East Foyer computer.
   - Survive the triggered wave.
   - Read the faxed Project Janus paper.

4. **Decode the Nursery chalkboard.**
   - The fax gives one random four-letter word: MOTH, CRAB, YETI or WORM.
   - At the Nursery board, find each letter's cluster.
   - The number of letters in that cluster becomes the corresponding digit.
   - Enter the resulting four-digit code in the service-tunnel keypad.

5. **Obtain the severed arm.**
   - Release the Doppelghast.
   - Kill it.
   - Take its severed arm.

6. **Claim the free Ray Gun Mark II.**
   - Bring the arm to the Armory fingerprint scanner.
   - Scan it.
   - Take the base Ray Gun Mark II.

7. **Collect three empty canisters.**
   - Pull one through the Rear Patio barrier using an LT53 Kazimir.
   - Destroy the correct blue crystal for another.
   - Recover the gas-tube canister through the valve/tube interaction chain.

8. **Build MKII-R / Rot Blight.**
   - Destroy the four active orange plants with explosive damage or the base MkII.
   - Collect four seeds.
   - Insert a canister at the Conservatory.
   - Plant one seed in each of four planters.
   - Defend each planter until the total charge reaches 100%.
   - Take the Toxic Canister.
   - Craft MKII-R at its workbench.

9. **Build MKII-P / Preservation.**
   - Break Project Janus boxes until the essence-bomb part appears.
   - Collect both purple refractors.
   - Blow open the Serpent Mound.
   - Install the canister and refractors.
   - Redirect the laser through the statue/crystal chain.
   - Kill the required Doppelghasts.
   - Take the Light Canister.
   - Craft MKII-P.

10. **Build MKII-W / Wraith Fire.**
    - Place the third canister at Shem's Henge.
    - Bait Abomination beams into the three quest rocks.
    - Use their charge attack to levitate the rocks.
    - Complete the resulting lockdown.
    - Take the Explosive Canister.
    - Craft MKII-W.

11. **Liminal Trial 1.**
    - Use the matching MkII variant to charge its portal with kills.
    - Complete the three-round sconce memory sequence.
    - Recover the bell.
    - Use a Brain-Rotted zombie at the Overlook bar to obtain the Nightcap flask.
    - Bring the Nightcap through the portal.
    - Break the shielded elite using the matching variant.
    - Interact with the Sentinel Artifact.

12. **Liminal Trial 2.**
    - Charge the next portal.
    - Find the three blood chalices.
    - Each reveals a two-digit number after its Elder Disciple encounter.
    - Read the three values in the required left-to-right order to form the six-digit safe code.
    - Open the safe and take the antler carving.
    - Return through the portal.
    - Defeat the shielded elite with the matching variant.
    - Interact with the Artifact again.

13. **Liminal Trial 3.**
    - Charge the Library portal.
    - Use Aether Shroud so the three liminal parts become visible.
    - Collect all three.
    - Observe the three glowing books.
    - Activate them in the correct order.
    - Open the secret route.
    - Defeat the final shielded elite with MKII-R.
    - Fully charge the Sentinel Artifact.

14. **Z-Rex boss.**
    - Commit through the S.A.M. panel/team vote.
    - Attack glowing eyes and the open mouth when available.
    - Prioritize the glowing green rib cage during damage windows.
    - Survive add phases at health thresholds.
    - Preserve a normal bullet weapon for ammo economy because the arena does not hand out scripted Max Ammo waves.

## Design observations

- Three weapon variants are not collectibles; each teaches a different interaction language before its matching ritual.
- Randomized codes remain fair because the current match contains the complete evidence.
- Failed planter steps are recoverable instead of silently soft-locking the run.
- Aether Shroud is reused as a perception tool, not only a combat ability.

---

# Black Ops 6 — Reckoning

## Main Quest dependency order

1. **Start the water/fungus setup immediately.**
   - Melee the mop bucket below the spawn sprinkler.
   - Run through the metal detectors so the bucket begins filling for later.
   - Pick up the syringe component in T1 Mutant Research while opening the map.

2. **Open Sublevel 10 and Pack-a-Punch.**
   - Use the Director's snow globe route.
   - Restart the particle accelerator.
   - Shoot all twelve Aetherium crystals.
   - Pack-a-Punch activates.

3. **Collect the blood sample.**
   - Jump into the active particle beam to become the floating orb.
   - Ram the suspended body so it falls.
   - Use the syringe on the body.
   - Retries are free if the movement attempt fails.

4. **Build Franken-Klaus.**
   - Shoot the arms off Commando Klaus enemies during special rounds; collect two.
   - Obtain the two legs in Android Assembly.
   - Assemble Franken-Klaus.

5. **Create Fowler's injection.**
   - Insert the blood-filled syringe at the Mutant Research console.
   - Kill the Fowler Mangler HVT.
   - Take the green injection.

6. **Beat the retina scanner.**
   - Activate Fowler's injection to become the mutant.
   - Use the retina scanner in Dark Entity Containment.
   - Open the hidden teleporter/boss-prep room.

7. **Solve the archive-date code.**
   - Find four documents around both towers.
   - Each contains a full archive date plus an item number.
   - Sort the documents by full date from oldest to newest.
   - Read their item numbers in that order.
   - Enter the resulting four-digit code.

8. **Complete the timed brain carry.**
   - Buy Melee Macchiato.
   - Melee the brain machine in T1 Quantum Computing.
   - Pick up the blue brain.
   - Carry it to the T2 Teleportation Lab before time expires.
   - A failed carry can be retried on a later round.

9. **Solve the periodic-table code.**
   - Read the two green words shown on the static monitors.
   - Take the first letter of each.
   - Treat those letters as a chemical-element symbol.
   - Convert that element to its atomic number.
   - Pad to three digits when necessary.
   - Use the number to open the Bioweapons Lab.

10. **Feed the cyst and drain the flora.**
    - Feed the quest cyst three vermin and three zombies.
    - Use the resulting progression to drain all three Aetheric Flora.

11. **Obtain the Gorgofex.**
    - Trigger the power surge.
    - Lure Uber Klaus onto the electrified plate.
    - Kill the resulting Forsaken-Klaus.
    - Claim the Gorgofex.

12. **Boost the Gorgofex and open the fungal route.**
    - Complete the selected Gorgofex upgrade path.
    - Use the upgraded weapon to break the portal crystals.
    - Recover the fungal head.

13. **Charge four vacuum-seal devices.**
    - Obtain the Project Janus vacuum devices.
    - Throw one at each purple floating quest object.
    - Recover the device after each use.
    - Fill all four.
    - Install them in the teleporter room.

14. **Final lockdown and allegiance choice.**
    - Complete the switch lockdown.
    - Open the boss portal.
    - Choose S.A.M. or Richtofen.
    - The choice changes the final encounter; Richtofen's route is substantially more demanding.

## Design observations

- Several puzzles randomize each match, but all data needed to solve them is present in-world.
- The brain run is a movement challenge with a clean next-round retry.
- The final narrative branch changes actual combat, giving the decision gameplay weight.

---

# Black Ops 7 — Astra Malorum

## Main Quest dependency order

1. **Repair the Harmonic Oculus and open Pack-a-Punch.**
   - Find its two missing components in Machina Astralis and the Luminarium.
   - Install both in the Observatory Dome.
   - Survive the defense.
   - Pack-a-Punch arrives.

2. **Gather the LGM-1 components.**
   - Shoot the small UFO orbiting O.S.C.A.R. for its damaged disc.
   - Find and shoot the one abnormal/blinking lamppost for the wires.
   - Shoot Old Tessie's bonnet with a Pack-a-Punched weapon for the battery.
   - Equip Cryofreeze and destroy the three purple crystals for three Absolute Zero shards.

3. **Kill O.S.C.A.R. three different trap ways.**
   - Observatory sunbeam.
   - Luminarium laser trap.
   - Museum rocket trap.
   - The third unique trap defeat completes the LGM-1 reward chain.

4. **Follow O.S.C.A.R. instead of fighting him.**
   - Trail a patrolling O.S.C.A.R. from behind.
   - Let the long "Elimination Twenty" monologue finish.
   - Record the three planets he names.
   - Convert each planet to its ordinal position from the sun.
   - Enter the resulting planet code.

5. **Extract the brain.**
   - Obtain the cryo key.
   - Get the bone saw.
   - Open the cryopod/subject route.
   - Remove the brain.
   - Survive the roughly one-minute lockdown.

6. **Read Mars' coordinates.**
   - Center Mars in the Observatory viewfinder.
   - Record the randomized declination value.
   - Enter the correctly formatted four-digit DEC value.

7. **Solve Thurston's reading list.**
   - Observe which book titles appear.
   - Each title maps to one of three library busts.
   - Count titles belonging to each bust.
   - Rotate each bust that many positions within the time limit.
   - Take Neptune.

8. **Align the planetary chandelier.**
   - Find the three planet notes.
   - Translate the notes into the required planet alignment.
   - Rotate/aim the chandelier planets.
   - Open the Mars teleport.

9. **Mars pylon/bird sequence.**
   - Shoot the five pylons in the correct order.
   - Follow/catch the bird interaction.
   - Obtain the Ascendant Eye.

10. **Organ-symbol sequence.**
    - Observe the five Harmonic Oculus symbols, including the static/noisy entry.
    - Reproduce the correct order on the Mars pillars.

11. **Caltheris boss.**
    - Charge the pylons.
    - Use them to fire the brain-powered laser.
    - Strip Caltheris' armor.
    - Repeat through phases.

12. **Final-phase hazard.**
    - In the last phase, treat the purple electrical pools as path-denial hazards rather than ordinary floor damage.
    - Maintain clean movement lanes while completing the final damage cycles.

## Design observations

- O.S.C.A.R. changes role repeatedly: roaming threat, source of a weapon part, trap target, and dialogue puzzle.
- The same NPC/enemy creates a coherent quest thread instead of isolated fetch steps.
- Astronomy is not decoration: planets, declination, books and observatory machinery all reinforce the map theme.

---

# Black Ops 7 — Paradox Junction

## Main Quest dependency order

1. **Learn the two timeline states.**
   - Destroyed/future Nuketown and Past/clean Nuketown hold different quest objects.
   - Hellhound rounds automatically flip the state.
   - The Temporal Storm/portal can also be used to change timelines.

2. **Open Trinity Avenue in the Past.**
   - In the Destroyed timeline, kill the golf-club zombie.
   - Take the truck keys.
   - Use them on the corresponding truck/path in the Past.

3. **Land Pack-a-Punch.**
   - Destroy the space-time knots around its Past-timeline site.
   - Repeat the required cycles until the machine drops into place.

4. **Build the Blundergat.**
   - Collect all four parts.
   - Assemble it at the Destroyed-timeline van bench.

5. **Upgrade to the Sundergat.**
   - Use the Blundergat to kill three tortured zombies at the relevant bench.
   - Move to the Past-timeline upgrade state.
   - Insert/complete the weapon interaction.
   - Claim the Sundergat.

6. **Reveal the Twins.**
   - Use the RC car interaction to open the garage.
   - Recover the chalk and swing-seat progression items.
   - Complete the reveal so the Twins manifest.

7. **Recruit the piano teacher.**
   - Apply Brain Rot to the required teacher zombie.
   - Follow her transition into the Past.

8. **Grow the tree and prepare the fire.**
   - Obtain the seeds.
   - Grow the quest tree.
   - Recover the three tomahawks.
   - Use the resulting progression to burn the firewood.

9. **Complete the toy-box setup.**
   - Recover the goggles.
   - Recover the headset.
   - Place both into the toy box.

10. **Complete the Twins' three children's games.**
    - Hopscotch: traverse the numbered pattern while avoiding the corrupted square.
    - Four square: melee the ball into different squares without repeating the same one.
    - Jacks: kill each airborne zombie before the bouncing ball lands.
    - Each failed game has a short retry rather than ending the run.
    - Escort each resulting gold item with Sundergat progress to its destination.

11. **Manipulate the clock across time.**
    - From the bus position, set the white clock hand to 12.
    - Set the red hand to 12.
    - Begin teleporting to the Past.
    - During the teleport animation, shoot the red hand once more so the final state becomes 12:05.
    - Follow the Twins' orb through the final locations.

12. **Dark Heart boss.**
    - Destroy the three black-goo nodes.
    - Hold the three concentration-field defenses.
    - When the heart becomes vulnerable, shoot the glowing cracks.
    - Repeat through the health thirds.

## Design observations

- The timeline mechanic affects almost every step; it is not just a visual gimmick.
- Children's games provide a deliberate genre shift while remaining thematically tied to Nuketown's domestic setting.
- The clock step weaponizes the actual transition animation, an unusually strong example of making traversal itself part of the puzzle.

---

# Black Ops 7 — Totenreich

## Main Quest dependency order

1. **Restore the facility and Pack-a-Punch.**
   - Repair both power lines.
   - Enter Tyr's head.
   - Use the console and take the Admin Keycard.
   - Open the War Factory admin room.
   - Obtain the GobbleDrop controller.
   - Drop/transport Pack-a-Punch to Fishery Island.

2. **Start the Jotunn Star.**
   - Wall-jump to obtain the Titan crane chain links.
   - Complete the chili/Zursa route for the chili chunks.

3. **Solve the constellation shrine.**
   - Activate the shrine positions in the required spatial order: left, right, back, front.

4. **Complete Astrid's soul-box route.**
   - Fill the required soul containers.
   - Open the lighthouse traversal.
   - Complete the parkour.
   - Claim the Jotunn Star.
   - The Star occupies the melee slot; its charged ranged attack becomes a later quest tool.

5. **Recover the flak round.**
   - Obtain the crowbar.
   - Read the cargo manifest.
   - Use the manifest to identify the matching crate.
   - Open it and take the flak shell.

6. **Shoot down the robot-head target.**
   - Load/fire the flak cannon.
   - Hit the correct robot-head objective.
   - Recover/install the transmitter in Tyr.

7. **Solve the communications waveform.**
   - Read the blinking-light information.
   - Translate it into the required oscilloscope amplitude and frequency.
   - Set both correctly.

8. **Recover Uranium 1.**
   - Drive the RC-XD into the genetic-lab route.
   - Complete the head puzzle.
   - Complete the lockpick step.
   - Take the first uranium objective.

9. **Recover Uranium 2.**
   - Catch/find the green fish.
   - Spawn the Ravager HVT.
   - Chase it through its three locations.
   - Complete the encounter for uranium two.

10. **Recover Uranium 3.**
    - Start the GobbleDrop challenge.
    - Kill only the designated floating zombies.
    - Complete the rule-clean challenge for uranium three.

11. **Recover and escort the Atomkraft Core.**
    - Use the claw machine.
    - Extract the core.
    - Escort it to Storm Bridge.

12. **Create the sunstone and light the bonfires.**
    - Transform the Dravakar shard into the sunstone.
    - Read the rune sequence.
    - Light the three rune bonfires in the required order.

13. **Boss.**
    - Break the red weak points.
    - Transition to the Viking-head targets.
    - Finish through the eye weak points.
    - Keep the Jotunn Star charged for interactions that depend on its ranged shot.

## Design observations

- Totenreich intentionally mixes movement, waveform reading, RC driving, fishing/HVT tracking, claw-machine interaction and combat.
- The Jotunn Star evolves from reward into a reusable traversal/quest verb.
- Distinct uranium routes keep three-item collection from feeling like three copies of the same task.

---

# Black Ops 7 — Kowakujō

## Main Quest dependency order

1. **Open the castle core.**
   - Capture both Ward banners.
   - Kill the Oni in the War Room.
   - Take the Shogun Hanko.
   - Use it to open the Shogun's Sanctum.

2. **Unlock Pack-a-Punch.**
   - Reach the World Seed.
   - Kill the marked/purple-aura enemies around it.
   - Fill the Seed.
   - Pack-a-Punch appears on the upper Sanctum floor.

3. **Take the easy-to-miss evidence immediately.**
   - Pick up the toxins note at the base of the Pack-a-Punch stairs.
   - This evidence is needed later for the murder deduction.

4. **Build the Maneki-Neko tactical.**
   - Collect its three parts.
   - Use the completed cat-grenade interaction to continue the Nekomancer chain.

5. **Recover the cat.**
   - Use PhD Flopper to smash/drop the cage.
   - Move the cage/cat through the molten-lava step.
   - Follow the paw-print trail.
   - Find the sleeping cat and scoop it up.

6. **Build the Nekomancer.**
   - Bring the cat to the World Seed.
   - Corrupt/transform the Seed through the required interaction.
   - Receive the Nekomancer Wonder Weapon.

7. **Lantern and Kitsune-mask sequence.**
   - Shoot all eleven lanterns rapidly with the Nekomancer.
   - Complete the ghostly-samurai interaction.
   - Use the rooftop glide/kite and catch the Fox Mask during flight.
   - Place the mask on its wall.
   - Complete the escalating Simon-says mask sequences.

8. **Reveal painting/evidence 1.**
   - Use the mask progression to uncover the first murder clue.

9. **Reveal painting/evidence 2.**
   - Work through the Coin Purse / gardener / merchant / nobleman clue branch.
   - Determine the accomplice clue.

10. **Reveal painting/evidence 3.**
    - Use the symptom/poison evidence.
    - Resolve among plum pit, monkshood and pufferfish as appropriate for the current match.

11. **Reveal painting/evidence 4.**
    - Complete the Kintsugi-bowl placement route.
    - Read the clue encoded in the resulting painting/background.

12. **Reveal painting/evidence 5.**
    - Read the four stopping values from the storage-room clock.
    - Interpret the randomized wall glyphs.
    - Place flags so each location's symbol values sum to the corresponding clock value.
    - Obtain the crest/medallion clue.

13. **Solve the murder.**
    - Combine accomplice, weapon/poison and location evidence.
    - Set the zodiac wheel to the uniquely deduced solution.
    - Light the incense / complete the ritual.
    - Defeat the resulting Onryo sequence and take the final boss route.

14. **Nyxara boss.**
    - Kill the flag-carrying Onis.
    - Plant/capture their flags in the marked zones.
    - Stand in the protected capture area for immunity.
    - Damage Nyxara's weak points in sequence: eyes, body, then wings.

## Design observations

- The quest is built around **investigation**, not just collection.
- The correct answer is deduced from several independent clues generated by the live match.
- A side mechanic — flags — is taught before becoming the boss's survival language.
- The easy-to-miss toxins note is a useful warning for Xziel: required evidence should have stronger recovery/visibility than optional lore.

---

# Black Ops 7 — Rex Infernus

## Main Quest dependency order

1. **Escape Her House.**
   - Survive until the phone rings.
   - Answer the Twins.
   - Use the cliff-side portal.
   - Reach the Nexus Forge.

2. **Forge Pack-a-Punch.**
   - Place the World Seed.
   - Follow the first Dread Skull to whichever temple it chooses this match.
   - Shoot it down.
   - Carry that temple's Usurped Flame back to one Forge brazier.
   - Repeat with the second Dread Skull and a different temple.
   - Turn both Forge crank wheels.
   - The platform lowers and exposes Pack-a-Punch.

3. **Acquire the temporary Void Claw.**
   - Pull a grapple charge from the green lantern/fountain sources.
   - Treat it as a renewable temporary tactical, not the Wonder Weapon.

4. **Recover the Fracture of Nyxara.**
   - Use lethal explosive damage on the wall above Dravakar's entrance.
   - Take the Fracture.

5. **Create the Astral Flame.**
   - Grapple the quest orb into the Pack-a-Punch/Nexus system.
   - Surge the Nexus.
   - Carry the Astral Flame to Nyxara's eye statue.

6. **Open Nyxara's Inner Sanctum.**
   - Redirect the laser through the crystal network.
   - Install the Fracture of Nyxara.
   - Open the Sanctum.

7. **Enter the Forest and recover the Wonder Weapon parts.**
   - Feed the vines.
   - Eat the fruit to enter the Forest/Astral Plane.
   - Search the three charred bodies.
   - Recover the Yankee Carbine part, Leather Strip and Protector's Bow.
   - The Forest can be revisited on later rounds if something was missed.

8. **Craft Warden's Blight.**
   - Travel to Dravakar's anvil.
   - Read/solve the randomized pillar riddle for the current match.
   - Install the three parts.
   - Craft the dual-crossbow Wonder Weapon.

9. **Upgrade the grapple.**
   - Return to Her House using the exfil-phone timing route.
   - Shoot the basketball through the broken-window interaction.
   - Record the four blue symbols.
   - Complete their input/route.
   - Obtain the Eye of the Forge.
   - This powers the stronger persistent boss-arena grapple system.

10. **Create rain and unlock the next environmental state.**
    - Solve the four-cube wall/portal chain.
    - Trigger the rain state required by later Corruption steps.

11. **Overdrive the Nexus generator.**
    - Rip open the required panels.
    - Clear the timed web blockages.
    - Supercharge the generator.
    - Align the three monoliths in front of the required temple.

12. **Cleanse all four temple Corruptions.**
    - Each temple has its own item/puzzle logic.
    - Acquire that temple's corrupted object.
    - Burn/purify it as instructed.
    - Read the Titan-shackle symbol.
    - Make the correct Titan arm kill the essence-marked target.
    - Complete the plate/reflector/statue interaction for that temple.
    - Use the orb/rain/flame state to finish the statue/forehead activation.
    - Repeat until all four Corruptions are cleansed.

13. **Boss preparation.**
    - Triple Pack-a-Punch a strong bullet weapon.
    - Upgrade Warden's Blight.
    - Bring armor recovery and preferably Aether Shroud.
    - Install/use the Eye of the Forge so grapple mobility remains dependable.
    - Stand on the blue circles below the Nexus generator.
    - Vote to descend.

14. **Warden boss core loop.**
    - Destroy the Warden's floating Dread Skull with Warden's Blight.
    - The skull's destruction stuns him briefly.
    - Swap to the bullet weapon.
    - Dump damage into the exposed top of the scorpion tail.
    - When he retreats to drain aether, kill the shadow souls around the arena; leaving them alive restores/hardens his armor.
    - Repeat through damage phases.

15. **Late boss phases.**
    - Clear ground stingers before they link into a wipe condition.
    - Survive the private trial room when teleported away.
    - Return for the apparent kill.
    - Expect the additional final phase after he gets back up.
    - Maintain armor because his late attacks can become lethal extremely quickly.

## Design observations

- Rex Infernus is a strong example of a long map where **one traversal tool (grapple)** is repeatedly recontextualized.
- Pack-a-Punch itself is a ritual reward, not merely a switch.
- Four temple branches share a grammar but differ enough that they do not collapse into repetitive soul-box chores.
- The boss deliberately assigns different jobs to the Wonder Weapon and conventional bullet weapon.

---

# Cross-map technical requirements exposed by these quests

These modern maps make a strong case that Xziel's generic quest system should support:

- per-match randomized clue generation;
- world-state/timeline layers;
- deterministic clue-to-solution validation;
- temporary tactical tools;
- carry-object states;
- timed movement routes;
- companion/special-enemy manipulation;
- enemy conversion/charm states;
- quest-specific weapon alt-fire;
- interactable physics objects;
- memory/Simon sequences;
- arithmetic/logic solvers;
- environment state changes such as rain;
- multi-stage boss weak points;
- side/branch choice persistence;
- retry policies per individual node;
- explicit point-of-no-return votes;
- solo equivalents for synchronized co-op interactions;
- authoritative quest snapshots for late join/reconnect.

The implementation goal for Xziel is **not to reproduce these quests**. It is to support this breadth of interaction cleanly enough that original maps can be authored from reusable components instead of custom spaghetti scripts.

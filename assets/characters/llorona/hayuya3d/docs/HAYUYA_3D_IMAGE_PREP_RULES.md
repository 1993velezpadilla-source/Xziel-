# HAYUYA 3D IMAGE PREP RULES

**Hayuya 3D** is the team's short name for **Hunyuan3D**.

## Automatic interpretation
When Christian, Félix, Volnox, or another teammate says:
- "prepare it for Hayuya 3D"
- "make refs for Hayuya"
- "make the photos for the 3D model"
- "create a photo for the 3D generator"

interpret that as this complete pipeline automatically.

## Mandatory pipeline
1. Lock a master visual reference.
2. Create a turnaround preview first.
3. Human approval before final individual exports.
4. Create all individual views.
5. Validate uniqueness of every orientation.
6. Validate visual consistency.
7. Save preview + individuals + manifest to the repo.
8. Only then hand off to Hayuya 3D / Hunyuan3D.

## Canonical 8-view set
1. Front
2. Front 45 Right
3. Right Side
4. Back 45 Right
5. Back
6. Back 45 Left
7. Left Side
8. Front 45 Left

## Hard anti-duplicate rule
Never accept a final set unless all eight orientations are unique.

Explicit checks:
- Front 45 Right != Front 45 Left
- Back 45 Right != Back 45 Left
- Right Side != Left Side
- A blind horizontal mirror is not a valid replacement when asymmetric details would become wrong.

## Visual consistency
Every view must preserve:
- same identity / face
- same hair and hair length
- same outfit
- same accessories
- same body proportions
- same damage / tears / wear logic
- same silhouette
- same general camera/scale presentation

## Framing
- portrait / vertical for individual views
- full body, head through feet/hem
- hands visible
- centered
- enough margin around silhouette
- neutral clean/dark background
- no environment clutter
- no aggressive perspective
- no major pose changes

## Preview-first rule
Preview exists to catch:
- missing orientations
- duplicated orientations
- mirror mistakes
- identity drift
- clothing drift
- crop/framing problems

Do not skip preview approval.

## Canonical filenames
```
<character>_front.png
<character>_front_45_right.png
<character>_right_side.png
<character>_back_45_right.png
<character>_back.png
<character>_back_45_left.png
<character>_left_side.png
<character>_front_45_left.png
```

## Team shorthand
**Hayuya 3D = Hunyuan3D prep pipeline.**

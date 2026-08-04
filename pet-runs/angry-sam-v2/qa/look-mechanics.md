# Angry Sam look mechanics

Angry Sam is a rigidly registered pixel-art humanoid. His shoes, lower legs, and pelvis stay anchored to the same baseline and horizontal center. The eyes and brows lead the gaze, followed by a restrained near-rigid head/neck turn and a small upper-torso follow-through. Facial proportions, clenched mouth, hair silhouette, jacket, fists, and shoes must remain unchanged; no whole-sprite rotation, broad raster warp, or skull stretching is allowed.

The motion budget is one even 22.5-degree step at a time. Pupils, eyelids, and brows move by a comparable amount at each step; head yaw or pitch follows gradually; shoulders shift only a few pixels. The fists remain attached and the jacket follows the torso without flipping sides. Scale, baseline, and lower-body registration stay constant through all 16 poses.

Cardinal pose families:

- 000 up: eyes and brows aim upward, chin lifts slightly, more underside of the brows/upper face reads while both body sides remain balanced.
- 090 screen-right: pupils, nose tip, and face turn clearly toward the image's right edge; the left side of the head becomes more visible and the right cheek recedes; shoulders follow subtly.
- 180 down: eyes aim down, upper lids lower, chin tucks, and the top of the hair becomes slightly more prominent without changing body scale.
- 270 screen-left: pupils, nose tip, and face turn clearly toward the image's left edge; the right side of the head becomes more visible and the left cheek recedes; shoulders follow subtly.

Diagonal poses interpolate these families evenly. The angry persona remains readable in every cell, and the clockwise loop must not reverse, snap, or pass through a neutral/front-facing pose.

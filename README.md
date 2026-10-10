# Void Hydra pet (Roblox)

**Blender model:** see [`blender/`](blender/README.md) for the `.blend`, an FBX ready for the Roblox 3D Importer, and renders. `PetFollower` uses that model automatically once it's imported as `ReplicatedStorage.VoidHydraModel`. Without it, the follower falls back to the Part-built version below.

A five-headed void hydra pet built only from Parts. The body uses Plastic with Studs surfaces, and the eyes, collars and summoning circle use Neon. It hovers over a spinning summoning circle, its necks sway, and glowing shards orbit around it.

## Install (no Rojo)

1. In Studio, add a **ModuleScript** to `ReplicatedStorage`, name it `VoidHydra`, and paste in `src/ReplicatedStorage/VoidHydra.lua`.
   For the Blender model, also add `src/ReplicatedStorage/ImportedPet.lua` as a ModuleScript named `ImportedPet`.
2. Add a **LocalScript** to `StarterPlayer > StarterPlayerScripts`, name it `PetFollower`, and paste in `src/StarterPlayer/StarterPlayerScripts/PetFollower.client.lua`.
3. Press Play. Every player gets a hydra that follows them.

With Rojo, run `rojo serve` and use the included `default.project.json`.

## Tweaking

Pass options to `VoidHydra.new({...})` (in `PetFollower`, through `PET_CONFIG`):

| Option | Default | What it does |
| --- | --- | --- |
| `Scale` | `0.35` | Studs per design unit. At 0.35 the pet is about 4 studs tall. |
| `Hover` | `0.8` | How high the body floats above the circle, in design units |
| `NeckCount` | `5` | Number of heads |
| `NeckSegments` | `4` | Blocks per neck |
| `CollarSegments` | `8` | Neon blocks in each neck collar |
| `RingSegments` | `28` | Blocks in the summoning circle |
| `ShardCount` | `8` | Orbiting neon shards |
| `Particles` / `Light` | `true` | Sparkle aura and chest light |

Colours are in `VoidHydra.Palette`.

The pet is drawn and animated on each client with `workspace:BulkMoveTo`, so the server does no work for it. With the defaults one pet has about 390 parts. Lower the segment counts if a server has many players.

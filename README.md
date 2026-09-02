# Dragonlight

Minecraft datapack. You can only get torches by killing the ender dragon.

The four torches on the exit portal pillar are the only ones in the world. Mine them off the
pillar. Respawn the dragon with four end crystals to get four more.

Java Edition, no mods, works on servers.

## Install

Download the zip for your version from `dist/` and put it in your world's datapacks folder.

- Singleplayer: `.minecraft/saves/<world>/datapacks/`
- Server: `<world>/datapacks/`

Run `/reload` or restart the world. Works on existing worlds.

## What it changes

Only drop when mined in the End:
torch, soul torch, copper torch, lantern, soul lantern, copper lantern.

No recipe and no drops at all:
candles, candle cakes, campfires, soul campfires.

These are also taken out of chest loot, trail ruins brushing, and villager trades.

Torches you place outside the End do not drop when you break them. Redstone torches and other
light sources are untouched.

## Supported versions

1.16.5, 1.17.1, 1.18.2, 1.19.2, 1.19.4, 1.20.1, 1.20.4, 1.20.6, 1.21.1, 1.21.4, 1.21.5,
1.21.8, 1.21.11, 26.1.2, 26.2

Use the closest version at or below yours.

## Add-ons

Optional. Install next to the main pack, same version.

- `redstone-torch-lock`: locks redstone torches too.
- `lenient-recovery`: lets you pick your own torches back up, except inside structures that
  generate torches. Needs 1.19 or newer.

## Building

```bash
python3 tools/build_dragonlight.py 1.21.4
```

Rebuilds the packs into `dist/`. Run it with no arguments to rebuild every version.

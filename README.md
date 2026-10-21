# ArkBug

### Bug fixes and compatibility tracking for Pumpkin

**Version: 0.1.0** · **26 issues covered**

ArkBug fixes several **Pumpkin** bugs, including crashes, data loss and gameplay issues. It comes with a patched version of the server and a plugin that displays the installed fixes.

The `/arkbug` command displays the server version and the fixes included in the running engine. Each issue number is clickable and links to its report on GitHub.

## Compatibility

| Component | Version |
| --- | --- |
| Plugin | ArkBug 0.1.0 |
| Pumpkin base | `0.2.0+26.3-26.51` |
| Included patched engine | `0.2.0+26.3-26.51.arkbug1` |
| Minecraft Java | 26.3 |

**Native fixes require the supplied engine or an equivalent build with the patches applied.** Installing only the WASM file adds the status command; it does not change the internal behavior of a standard Pumpkin engine.

This release was tested on Linux with Java clients. Bedrock validation is not covered by this release.

## Included fixes

The links point to issue reports in the Pumpkin repository. The descriptions cover the fixes implemented by ArkBug.

| Issue | Fix |
| --- | --- |
| [#3844](https://github.com/Pumpkin-MC/Pumpkin/issues/3844) | Fixes crossbow and component serialization, including loading, firing and persistence after reconnecting. |
| [#3759](https://github.com/Pumpkin-MC/Pumpkin/issues/3759) | Limits the depth and command count of function chains; supports namespaced identifiers. |
| [#4048](https://github.com/Pumpkin-MC/Pumpkin/issues/4048) | Removes reference cycles that kept players in memory after they disconnected. |
| [#3516](https://github.com/Pumpkin-MC/Pumpkin/issues/3516) | Enforces the light threshold for natural crop and stem growth. |
| [#4089](https://github.com/Pumpkin-MC/Pumpkin/issues/4089) | Accounts for firework rocket flight duration, including when flying with an Elytra. |
| [#3972](https://github.com/Pumpkin-MC/Pumpkin/issues/3972) | Sends an update to clients when a dispenser places powder snow. |
| [#4123](https://github.com/Pumpkin-MC/Pumpkin/issues/4123) | Adds the impact animation and sound for the Warden’s melee attacks. |
| [#3847](https://github.com/Pumpkin-MC/Pumpkin/issues/3847) | Preserves changes to the held item during block interactions. |
| [#3918](https://github.com/Pumpkin-MC/Pumpkin/issues/3918) | Prevents a trident from repeatedly dealing damage while remaining in contact with the same mob. |
| [#3933](https://github.com/Pumpkin-MC/Pumpkin/issues/3933) | Preserves the correct bucket after capturing an aquatic mob, including with the offhand. |
| [#3969](https://github.com/Pumpkin-MC/Pumpkin/issues/3969) | Correctly places bucket contents on aquatic vegetation and in positions already filled with water. |
| [#4063](https://github.com/Pumpkin-MC/Pumpkin/issues/4063) | Fixes fish behavior out of water, including flopping, air supply and suffocation damage. |
| [#4090](https://github.com/Pumpkin-MC/Pumpkin/issues/4090) | Fixes fish constantly rising to the surface; adjusts swimming movement for regular and glow squids. |
| [#3989](https://github.com/Pumpkin-MC/Pumpkin/issues/3989) | Fixes the crash caused by placing a vault (`vault`). |
| [#3065](https://github.com/Pumpkin-MC/Pumpkin/issues/3065) | Fixes the particle packet used when eyeblossoms transform. |
| [#3716](https://github.com/Pumpkin-MC/Pumpkin/issues/3716) | Decodes packet IDs in the correct state for WASM packet observers. |
| [#3698](https://github.com/Pumpkin-MC/Pumpkin/issues/3698) | Prevents invalid NBT that could make a chunk containing a decorated map unreadable. See the limitation on decorations below. |
| [#3730](https://github.com/Pumpkin-MC/Pumpkin/issues/3730) | Fixes profile serialization for custom player heads to prevent related disconnections. |
| [#2016](https://github.com/Pumpkin-MC/Pumpkin/issues/2016), [#4045](https://github.com/Pumpkin-MC/Pumpkin/issues/4045) | Processes block update cascades iteratively, preventing stack overflows reproduced with saplings, pressure plates and fire. |
| [#3902](https://github.com/Pumpkin-MC/Pumpkin/issues/3902) | Preserves chest and other block entity data before unloading chunks associated with players. |
| [#3571](https://github.com/Pumpkin-MC/Pumpkin/issues/3571) | Preserves book titles and pages, their styles and colors, filtered variants and metadata. |
| [#3510](https://github.com/Pumpkin-MC/Pumpkin/issues/3510) | Reports failures when copying or replacing `level.dat`, which were previously ignored. |
| [#3367](https://github.com/Pumpkin-MC/Pumpkin/issues/3367) | Reads gamerules, weather and wandering trader data from the Paper/Purpur overworld container when root files are missing. |
| [#3511](https://github.com/Pumpkin-MC/Pumpkin/issues/3511) | Writes player data to a temporary file before replacing the existing file, preserving the last valid save if writing fails. |
| [#3512](https://github.com/Pumpkin-MC/Pumpkin/issues/3512) | Orders player saves to prevent an older periodic snapshot from overwriting a newer save. |

Issues #2016 and #4045 share a single patch: the catalog therefore covers **26 issues with 25 distinct patches**.

## Validation

The supplied evidence documents tests on disposable servers: connections, inventories, restarts, failed writes, concurrent saves and block update cascades. Book, profile, particle and item packets are also checked using the official Mojang Java 26.3 codecs.

The manifest lists file hashes, the checks performed and those reused when the relevant code remains unchanged. Automated tests do not constitute manual visual validation or a guarantee that no bugs remain.

## Reporting an issue

Include the version shown by `/arkbug`, the relevant issue number if known, reproduction steps, useful logs and installed plugins. Specify whether the problem occurs with the supplied ArkBug engine or another Pumpkin build.

## Credits and license

**ArkBug author: Arklandia Studios.**

ArkBug builds on [Pumpkin](https://github.com/Pumpkin-MC/Pumpkin) and the work of its community. Some adaptations draw on upstream proposals [#3897](https://github.com/Pumpkin-MC/Pumpkin/pull/3897), [#3813](https://github.com/Pumpkin-MC/Pumpkin/pull/3813), [#3924](https://github.com/Pumpkin-MC/Pumpkin/pull/3924), [#3634](https://github.com/Pumpkin-MC/Pumpkin/pull/3634) and [#3537](https://github.com/Pumpkin-MC/Pumpkin/pull/3537). References and evidence of these adaptations are kept with the sources.

License: **GPL-3.0-only**. See the `LICENSE` file supplied with the sources.

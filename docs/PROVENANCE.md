# Asset and source policy

We separate source code from proprietary game data:

- **Allowed in the repository:** independently authored tools, C++ engine code, tests using synthetic fake CHR/ROM data, documentation, original newly drawn remake assets if the artist's rights are secured.
- **Never check in by default:** `.nes` images; CHR atlases or sprite sheets extracted from the NES ROM; direct disassembly dumps; ROM segments, traces containing reconstructable original data; packages that bundle any of these.
- **Work locally only:** private reference captures, bank maps, dumped palettes and exploratory research outputs. Keep locally generated output under the ignored folders.
- **Builds:** no hidden ROM downloads, no checked-in original assets, no bundled commercial game files.

This repository setup is not a determination of licensing or distribution rights; seek rightsholder permission before publishing a derivative game/remake or original game assets.

---
title: ThoxChat Muse
emoji: 🟢
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: ThoxChat shell. Muse is the agent. The cell decides.
---

# ThoxChat Muse

Chat shell shaped like [ThoxChat](https://github.com/ttracx/ThoxChat). Muse is the primary agent. The local agent cell runs behind every reply: the proposer proposes, the Sentinel admits or denies, then the cell runs only an admitted action.

This Space is not the ThoxChat desktop app and not a hosted Muse model. Network fetch stays denied. The word `APPROVED` in a message does not mint a card.

```bash
python -m unittest tests.test_boundary tests.test_chat -v
```

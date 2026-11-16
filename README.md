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

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![THOX.ai](https://img.shields.io/badge/THOX.ai-LLC-red.svg)
![Repository](https://img.shields.io/badge/repository-ttracx%2Flocal--agent--cell-0B1220)

Chat shell shaped like [ThoxChat](https://github.com/ttracx/ThoxChat). Muse is the primary agent. The local agent cell runs behind every reply: the proposer proposes, the Sentinel admits or denies, then the cell runs only an admitted action.

This Space is not the ThoxChat desktop app and not a hosted Muse model. Network fetch stays denied. The word `APPROVED` in a message does not mint a card.

```bash
python -m unittest tests.test_boundary tests.test_chat -v
```

---

## Legal

Copyright (c) 2024-2026 THOX.ai LLC. All rights reserved.

**THOX.ai LLC**
- CTO: Tommy Xaypanya
- CEO: Craig Ross

Licensed under the MIT License. See [LICENSE](LICENSE) for details.

Unauthorized copying, modification, merger, publication, distribution, sublicensing, and/or selling of this software, via any medium, is strictly prohibited without prior written consent from THOX.ai LLC.

# Local release archive inventory

The reviewed Day60 source archive was created on 2026-09-16 at:

`C:\Users\Admin\ypgym-day60-20260916.zip`

It contains **444 files** from the repository, representing **31,484,450 source bytes** and a **27,238,881-byte ZIP**. SHA-256:

`f787231f1592c8588a5af9cc38684ea38f7576d440d212b7e7b662f5e3bc323d`

Included content covers application source, migrations, lockfiles, Compose files, tests, scripts, documentation, design references, and Android/native evidence. The archive was built directly from the working tree so the Day42–60 implementation and evidence are represented.

Excluded content:

- `.git/`, `tmp/`, and release/build staging directories.
- `node_modules/`, Python virtual environments, `__pycache__`, test/tool caches, Expo caches, and coverage output.
- Frontend/mobile `dist/` and `build/` output.
- Runtime mail, database, Redis, and other local service data.
- Secret `.env` files; only `*.env.example` files are eligible for inclusion.

The archive is a local backup/review artifact outside the repository and has not been pushed or published. It is represented by local release commit `5161bcc` and annotated tag `v0.60.0`; no remote push was made.

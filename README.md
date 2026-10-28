# Nimbo Simplified Chinese Patch (Unofficial)

[简体中文说明](README.zh-CN.md) | English

This tool makes a separate Simplified Chinese copy of a **verified original** macOS Nimbo application. It does not modify the original. It is a patcher to run again after an update, **not a plugin or an automatic update service**. Only byte-for-byte verified 0.6.2 and 0.6.3 releases are accepted. Future Nimbo releases require fresh verification and may not be compatible.

This repository **does not distribute Nimbo binaries, icons, installers, extracted frontend source, or signatures**. Nimbo belongs to its original authors. The MIT license here covers only this patcher and its Chinese translation, not Nimbo itself. This project is not affiliated with Nimbo.

## Supported Releases

| Nimbo version | Platform | Verification |
| --- | --- | --- |
| 0.6.2 | macOS universal app | Local original hash and static checks of both architectures |
| 0.6.3 | macOS universal app | [Official release archive](https://github.com/EmilMoe/binaries/releases/tag/nimbo-v0.6.3) and static checks of both architectures |

The patch translates 510 frontend strings. Native menus and some file-type names remain in English. Chinese is the default unless a previous language preference was saved; select "简体中文" in Nimbo's language setting in that case. The interface and S3 connections have **not** been independently tested in an isolated account.

## Installation and Configuration

Requirements: macOS, Python 3.10+, Node.js 18+, and Git. Node checks the syntax of the modified JavaScript; it **does not execute it**.

```bash
git clone https://github.com/xizai12/nimbo-zh-patch.git
cd nimbo-zh-patch
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
node --version
```

First validate your **unmodified original** Nimbo app. Dry-run does not write an app:

```bash
python patch_nimbo.py --source '/Applications/Nimbo.app' --dry-run
python patch_nimbo.py --source '/Applications/Nimbo.app'
```

The second command creates `Nimbo 中文 <version>.app` in this repository directory. The version is determined by your original: if it is 0.6.2, the output is also 0.6.2. The patcher **does not download 0.6.3**. The source executable, translations, embedded resources for both architectures, icon, `Info.plist`, and bundle structure must pass verification. A mismatch stops the patch. Output must be a **new** `.app` path inside this repository or its subdirectories. Existing copies cannot be overwritten, and the original or `/Applications` cannot be the output.

To use another output name, pass an absolute path within the repository. The app's internal display name follows the output filename:

```bash
python patch_nimbo.py --source '/Applications/Nimbo.app' \
  --output "$PWD/Nimbo.app"
```

This creates a separate copy named `Nimbo.app` **inside the repository**, not in `/Applications`. It does not remove or replace the original. Do not replace the original until the copy has been evaluated under a separate macOS user account with test credentials; keep a backup for rollback.

### Using the Official 0.6.3 Archive

Download the macOS `Nimbo.app.tar.gz` from the [official 0.6.3 release](https://github.com/EmilMoe/binaries/releases/tag/nimbo-v0.6.3) into `~/Downloads`. The verified SHA-256 for this archive is:

```text
86098243bf0f6cf5a098020c3c9cb24ed771d35c5a77c0384d383968ea9265fe
```

**Check the downloaded archive's hash first**, then unpack into a separate directory and use that original app:

```bash
shasum -a 256 "$HOME/Downloads/Nimbo.app.tar.gz"
mkdir -p "$HOME/Downloads/nimbo-0.6.3-original"
tar -xzf "$HOME/Downloads/Nimbo.app.tar.gz" -C "$HOME/Downloads/nimbo-0.6.3-original"
python patch_nimbo.py --source "$HOME/Downloads/nimbo-0.6.3-original/Nimbo.app" --dry-run
python patch_nimbo.py --source "$HOME/Downloads/nimbo-0.6.3-original/Nimbo.app"
```

If the archive hash differs, **do not unpack or run it**. These commands do not install either app into `/Applications`.

### Changing the Translation

Edit [zh.json](zh.json), preserving all 510 keys, array lengths, and placeholders such as `{name}`. Run dry-run again. The patcher rejects translations that cannot fit into the original compressed resource slots. An existing generated app is not updated automatically; use a new `--output` name after changing the translation.

## Updates, Risks, and Rollback

- Official Nimbo updates do not preserve this patch. Re-run it on a **new clean original**; unknown releases are rejected. Supporting a future version requires independent checks of the release, offsets in both architectures, translations, and hashes. Never use a previously patched copy as input.
- The modified app is **unsigned and not notarized**. macOS may prevent it from launching. Do not globally disable macOS protections or bulk-remove quarantine to run it.
- The copy keeps the original bundle ID and may share local preferences and S3 credentials with the original app. Evaluate it only under a **separate macOS user account** with test credentials; do not use it with your real S3 account yet.
- The patch removes the startup automatic update check but **does not** fully disable the manual update interface. Do not update from inside the patched copy.
- To roll back, stop using the Chinese copy and run the original. Do not delete or migrate shared application data. Generated `.app` bundles are ignored by Git to avoid accidental publication.

The tool does not inject into processes, install scheduled tasks, or download updates. Run unit tests with `python -m unittest discover -s tests -v`. Because upstream binaries are not distributed here, complete integration checks require your own verified original app and a `--dry-run`.

"""Build an isolated Simplified Chinese copy of a verified Nimbo release.

This replaces the Danish frontend slot in a copy only; native menus stay English.
It never modifies /Applications/Nimbo.app or overwrites an existing output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import plistlib
import random
import re
import shutil
import string
import subprocess

import brotli
import json5

ROOT = pathlib.Path(__file__).resolve().parent
EXECUTABLE = pathlib.Path("Contents/MacOS/s3client")
VERIFIED_RELEASES = {
    "0.6.2": (
        "0b7f36d16ced496390524fb96f0439ca53be769a4f862cb3bbbf7568600e1569",
        (17928870, 34745982),
        (17943625, 34760737),
    ),
    "0.6.3": (
        "92a27fc6d6dae708b8e0ed2f0884ec06274a24067d00a33d5cc82860dbd948fa",
        (17921696, 34755256),
        (17936451, 34770011),
    ),
}
ASSET_SIZES_AND_HASHES = {
    "i18n": (12862, "955f5b43114fafeca2144f5abfe2eb7861885f1a4a7363b7da28707c06fe6d04"),
    "main": (53748, "628c0d93a5e4810c114d01b896e14c795fab8f5161cf7609f807e0d29a2257a5"),
}
BUNDLE_HASHES = {
    "0.6.2": (
        "f0dd2570412a227111dea4ddfc7984775486a55c841aa0847528ddc0a9d4ecc9",
        "4b133baef356126f8da19f6b5832290cd1a3e3a8288901cfc665455ce16165e4",
    ),
    "0.6.3": (
        "ba21bb79723d020228bc7ef6d79c68414ef066a67bb73631f0a606fa1bc42e93",
        "973ba86625a216c2e0374c3bdc11cadce363cbd9f71faf63068f6d216e1014fd",
    ),
}
EXPECTED_ENTRIES = {
    pathlib.Path("Contents"),
    pathlib.Path("Contents/Info.plist"),
    pathlib.Path("Contents/MacOS"),
    EXECUTABLE,
    pathlib.Path("Contents/Resources"),
    pathlib.Path("Contents/Resources/icon.icns"),
}
PLACEHOLDER = re.compile(r"\{(\w+)\}")
ALPHABET = string.ascii_letters + string.digits


def check_translation(source: str, translated: dict[str, object]) -> None:
    english = json5.loads("{" + source.split("const en = {", 1)[1].split("\n};", 1)[0] + "}")
    if set(translated) != set(english):
        raise ValueError(f"Translation keys differ: missing={set(english) - set(translated)}, extra={set(translated) - set(english)}")
    for key, original in english.items():
        value = translated[key]
        if type(value) is not type(original) or (isinstance(value, list) and len(value) != len(original)):
            raise ValueError(f"Translation shape differs: {key}")
        originals = original if isinstance(original, list) else [original]
        values = value if isinstance(value, list) else [value]
        for a, b in zip(originals, values):
            if not isinstance(b, str) or sorted(PLACEHOLDER.findall(a)) != sorted(PLACEHOLDER.findall(b)):
                raise ValueError(f"Translation placeholders differ: {key}")
    print(f"Validated {len(english)} translated keys and placeholders")


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Expected exactly one source occurrence of {old[:60]!r}")
    return source.replace(old, new, 1)


def translated_i18n(source: str, translated: dict[str, object]) -> str:
    check_translation(source, translated)
    prefix, remainder = source.split("const da = {", 1)
    _, suffix = remainder.split("\n};", 1)
    compact = json.dumps(translated, ensure_ascii=False, separators=(",", ":"))
    result = prefix + "const da = " + compact + ";" + suffix
    result = replace_once(result, "/** Translates `key`, filling {placeholders}; arrays pick singular/plural by params.n. */\n", "")
    result = replace_once(result, 'const LOCALES = { da: "da-DK", en: "en-US" };', 'const LOCALES = { da: "zh-CN", en: "en-US" };')
    result = replace_once(result, "document.documentElement.lang = lang;", 'document.documentElement.lang = lang === "da" ? "zh-CN" : lang;')
    result = replace_once(result, "export const kindName = (ext) => KINDS[lang][ext];", 'export const kindName = (ext) => KINDS[lang === "da" ? "en" : lang][ext];')
    return result


def translated_main(source: str) -> str:
    result = replace_once(source, '[["da", "Dansk"], ["en", "English"]]', '[["da", "简体中文"], ["en", "English"]]')
    result = replace_once(result, 'navigator.language.startsWith("da")', 'true')
    # The native backend only has Danish/English; use English native menus.
    result = replace_once(result, 'invoke("set_language", { lang })', 'invoke("set_language", { lang: lang === "da" ? "en" : lang })')
    result = replace_once(result, "/** S3 folders with at least this many objects get a warning before renaming. */\n", "")
    result = replace_once(result, "  autoCheckUpdate();\n}", "  // No automatic update in this isolated translation test.\n}")
    return result


def fit_brotli(script: str, expected_size: int, quality: int) -> tuple[bytes, bytes]:
    raw = script.encode("utf-8")
    initial = brotli.compress(raw, quality=quality)
    if len(initial) == expected_size:
        return raw, initial
    if len(initial) > expected_size:
        raise ValueError(f"Compressed asset exceeds its slot: {len(initial)} > {expected_size}")

    # A harmless JS comment lets Brotli fill the fixed-size embedded byte slice.
    gap = expected_size - len(initial)
    for seed in range(8):
        rng = random.Random(seed)
        chars = "".join(rng.choices(ALPHABET, k=gap * 3 + 160))
        for count in range(gap * 3 + 161):
            padded = raw + b"\n/*" + chars[:count].encode("ascii") + b"*/\n"
            encoded = brotli.compress(padded, quality=quality)
            if len(encoded) == expected_size:
                return padded, encoded
            if count > gap * 2 + 80 and len(encoded) > expected_size + 50:
                break
    raise ValueError(f"Could not fit compressed asset exactly in {expected_size} bytes")


def verify_js(raw: bytes) -> None:
    result = subprocess.run(["node", "--check", "--input-type=module"], input=raw, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", "replace"))


def build(source_app: pathlib.Path, output_app: pathlib.Path | None, dry_run: bool) -> None:
    source_app = source_app.resolve(strict=True)
    if not source_app.is_dir() or source_app.suffix != ".app":
        raise ValueError("Source must be a Nimbo .app directory")
    entries = list(source_app.rglob("*"))
    if {entry.relative_to(source_app) for entry in entries} != EXPECTED_ENTRIES or any(entry.is_symlink() for entry in entries):
        raise ValueError("Source bundle has missing, extra, or linked files; refusing to copy it")
    info_bytes = (source_app / "Contents/Info.plist").read_bytes()
    info = plistlib.loads(info_bytes)
    version = info.get("CFBundleShortVersionString")
    if info.get("CFBundleIdentifier") != "dk.moegroup.s3browser" or version not in VERIFIED_RELEASES:
        raise ValueError("Unknown Nimbo identity or version; refusing to patch")
    info_hash, icon_hash = BUNDLE_HASHES[version]
    if hashlib.sha256(info_bytes).hexdigest() != info_hash:
        raise ValueError("Source Info.plist differs from the verified release")
    if hashlib.sha256((source_app / "Contents/Resources/icon.icns").read_bytes()).hexdigest() != icon_hash:
        raise ValueError("Source icon differs from the verified release")
    expected_hash, i18n_offsets, main_offsets = VERIFIED_RELEASES[version]
    assets = {
        "i18n": (i18n_offsets, *ASSET_SIZES_AND_HASHES["i18n"]),
        "main": (main_offsets, *ASSET_SIZES_AND_HASHES["main"]),
    }
    binary = (source_app / EXECUTABLE).read_bytes()
    if hashlib.sha256(binary).hexdigest() != expected_hash:
        raise ValueError("Source executable differs from the verified release; refusing to patch")
    if output_app is None:
        output_app = ROOT / f"Nimbo 中文 {version}.app"
    if not output_app.is_absolute():
        raise ValueError("Output path must be absolute")
    if output_app.suffix != ".app" or not output_app.parent.is_dir():
        raise ValueError("Output must be a new .app in an existing directory")
    output_parent = output_app.parent.resolve()
    if not output_parent.is_relative_to(ROOT):
        raise ValueError("Output must stay inside the translation workspace")
    if (output_app.resolve() == source_app or output_parent.is_relative_to(source_app)
            or source_app.is_relative_to(output_app.resolve())):
        raise ValueError("Refusing to patch source app in place")
    if not dry_run and (output_app.exists() or output_app.is_symlink()):
        raise FileExistsError(f"Refusing to overwrite existing output: {output_app}")
    translated = json.loads((ROOT / "zh.json").read_text(encoding="utf-8"))
    patched = bytearray(binary)
    for name, (offsets, size, expected_hash) in assets.items():
        original = [brotli.decompress(binary[offset : offset + size]) for offset in offsets]
        if len(set(original)) != 1 or hashlib.sha256(original[0]).hexdigest() != expected_hash:
            raise ValueError(f"Embedded {name} asset does not match the verified source")
        source = original[0].decode("utf-8")
        edited = translated_i18n(source, translated) if name == "i18n" else translated_main(source)
        raw, encoded = fit_brotli(edited, size, 11 if name == "i18n" else 9)
        verify_js(raw)
        for offset in offsets:
            patched[offset : offset + size] = encoded
            if brotli.decompress(patched[offset : offset + size]) != raw:
                raise ValueError(f"Patched {name} asset failed round-trip validation")
        print(f"{name}: {len(original[0])} -> {len(raw)} decoded bytes; {len(encoded)} fixed-size compressed bytes per architecture")
    print("Patched executable SHA256:", hashlib.sha256(patched).hexdigest())
    if dry_run:
        print("Dry run complete. Original app unchanged; no copy written.")
        return

    shutil.copytree(source_app, output_app, symlinks=True)
    (output_app / EXECUTABLE).write_bytes(patched)
    clone_info_path = output_app / "Contents/Info.plist"
    clone_info = plistlib.loads(clone_info_path.read_bytes())
    clone_info["CFBundleDisplayName"] = f"Nimbo 中文 {version}"
    clone_info["CFBundleName"] = f"Nimbo 中文 {version}"
    clone_info_path.write_bytes(plistlib.dumps(clone_info))
    if clone_info["CFBundleShortVersionString"] != version:
        raise ValueError("Copied bundle version changed during creation")
    copy_binary = (output_app / EXECUTABLE).read_bytes()
    if hashlib.sha256(copy_binary).digest() != hashlib.sha256(patched).digest():
        raise ValueError("Copied executable changed during creation")
    for offsets, size, _ in assets.values():
        for offset in offsets:
            brotli.decompress(copy_binary[offset : offset + size])
    print(f"Created and verified isolated copy: {output_app}")
    print("Source app untouched. This copy is not signed or notarized and must be tested before use with S3 credentials.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=pathlib.Path("/Applications/Nimbo.app"), help="verified original Nimbo.app to copy")
    parser.add_argument("--output", type=pathlib.Path, help="absolute path for a new isolated .app (never overwritten)")
    parser.add_argument("--dry-run", action="store_true", help="validate and size assets without writing a copy")
    args = parser.parse_args()
    build(args.source, args.output, args.dry_run)

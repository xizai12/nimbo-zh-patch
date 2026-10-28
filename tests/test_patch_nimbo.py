import hashlib
import pathlib
import plistlib
import tempfile
import unittest
from unittest import mock

import patch_nimbo as patcher


def digest(data):
    return hashlib.sha256(data).hexdigest()


class TranslationTests(unittest.TestCase):
    def test_replacement_requires_unique_match(self):
        self.assertEqual(patcher.replace_once("abc", "b", "B"), "aBc")
        with self.assertRaises(ValueError):
            patcher.replace_once("bbb", "b", "B")

    def test_translation_keeps_keys_and_placeholders(self):
        source = 'const en = {\n  hello: "Hello {name}",\n  items: ["{n} item", "{n} items"]\n};'
        patcher.check_translation(source, {"hello": "你好 {name}", "items": ["{n} 项", "{n} 项"]})
        with self.assertRaisesRegex(ValueError, "Translation keys differ"):
            patcher.check_translation(source, {"hello": "你好 {name}"})
        with self.assertRaisesRegex(ValueError, "Translation placeholders differ"):
            patcher.check_translation(source, {"hello": "你好", "items": ["{n} 项", "{n} 项"]})


class SourceValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.source = self.root / "Nimbo.app"
        (self.source / "Contents/MacOS").mkdir(parents=True)
        (self.source / "Contents/Resources").mkdir()
        self.info_path = self.source / "Contents/Info.plist"
        self.icon_path = self.source / "Contents/Resources/icon.icns"
        self.exe_path = self.source / patcher.EXECUTABLE
        self.set_version("0.6.3")
        self.icon_path.write_bytes(b"icon")
        self.exe_path.write_bytes(b"executable")

    def set_version(self, version):
        self.info_path.write_bytes(plistlib.dumps({
            "CFBundleIdentifier": "dk.moegroup.s3browser",
            "CFBundleShortVersionString": version,
        }))

    def trust_fixture(self):
        hashes = (digest(self.info_path.read_bytes()), digest(self.icon_path.read_bytes()))
        return (
            mock.patch.dict(patcher.BUNDLE_HASHES, {"0.6.3": hashes}),
            mock.patch.dict(patcher.VERIFIED_RELEASES, {
                "0.6.3": (digest(self.exe_path.read_bytes()), (), ())
            }),
        )

    def test_unknown_version_is_rejected(self):
        self.set_version("0.6.4")
        with self.assertRaisesRegex(ValueError, "Unknown Nimbo identity or version"):
            patcher.build(self.source, None, True)

    def test_extra_file_is_rejected(self):
        (self.source / "Contents/Resources/extra.txt").write_text("do not copy")
        with self.assertRaisesRegex(ValueError, "missing, extra, or linked"):
            patcher.build(self.source, None, True)

    def test_linked_file_is_rejected(self):
        self.icon_path.unlink()
        self.icon_path.symlink_to(self.exe_path)
        with self.assertRaisesRegex(ValueError, "missing, extra, or linked"):
            patcher.build(self.source, None, True)

    def test_modified_icon_is_rejected(self):
        with mock.patch.dict(patcher.BUNDLE_HASHES, {
            "0.6.3": (digest(self.info_path.read_bytes()), digest(b"original icon"))
        }):
            with self.assertRaisesRegex(ValueError, "Source icon differs"):
                patcher.build(self.source, None, True)

    def test_modified_executable_is_rejected(self):
        with mock.patch.dict(patcher.BUNDLE_HASHES, {
            "0.6.3": (digest(self.info_path.read_bytes()), digest(self.icon_path.read_bytes()))
        }):
            with self.assertRaisesRegex(ValueError, "Source executable differs"):
                patcher.build(self.source, None, True)

    def test_output_must_remain_in_repo_and_not_overwrite(self):
        repo = self.root / "repo"
        repo.mkdir()
        trusted_bundle, trusted_executable = self.trust_fixture()
        with trusted_bundle, trusted_executable, mock.patch.object(patcher, "ROOT", repo):
            with self.assertRaisesRegex(ValueError, "inside the translation workspace"):
                patcher.build(self.source, self.root / "outside.app", False)
            existing = repo / "existing.app"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                patcher.build(self.source, existing, False)

    def test_output_cannot_be_nested_under_source(self):
        trusted_bundle, trusted_executable = self.trust_fixture()
        with trusted_bundle, trusted_executable, mock.patch.object(patcher, "ROOT", self.root):
            with self.assertRaisesRegex(ValueError, "in place"):
                patcher.build(self.source, self.source / "nested.app", False)


if __name__ == "__main__":
    unittest.main()

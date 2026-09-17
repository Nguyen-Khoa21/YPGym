from pathlib import Path
import hashlib
import json
import tempfile
import unittest
import zipfile

from package_release import is_release_source, write_archive


class ReleasePackageTests(unittest.TestCase):
    def test_runtime_and_secret_paths_are_excluded(self):
        for name in ["backend/storage/invoices/example.pdf", "backend/Storage/invoices/example.pdf", "backend/.env", "mobile/.env.local", "tmp/capture.png", "frontend/node_modules/pkg/index.js", "mobile/dist/app.js", "device.key", "../private.txt"]:
            with self.subTest(name=name):
                self.assertFalse(is_release_source(name))
        for name in ["backend/.env.example", "frontend/package-lock.json", "docs/diagrams/ypgym-erd.drawio", "docs/design/evidence/qr.png"]:
            with self.subTest(name=name):
                self.assertTrue(is_release_source(name))

    def test_archive_contains_source_and_manifest_without_runtime_invoice(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "backend/storage/invoices").mkdir(parents=True)
            (root / "README.md").write_text("release source", encoding="utf-8")
            (root / "backend/storage/invoices/private.pdf").write_bytes(b"private invoice")
            output = root / "release.zip"
            result = write_archive(root, ["README.md", "backend/storage/invoices/private.pdf"], output, "test-revision")
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()), {"README.md", "ARCHIVE-CONTENTS.json"})
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read("ARCHIVE-CONTENTS.json"))
                self.assertEqual(manifest["files"][0]["sha256"], hashlib.sha256(archive.read("README.md")).hexdigest())
            self.assertEqual(result["file_count"], 1)
            self.assertEqual(result["excluded_candidates"], ["backend/storage/invoices/private.pdf"])

    def test_link_to_file_outside_repository_is_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            root = parent / "repo"
            root.mkdir()
            private = parent / "private.txt"
            private.write_text("private", encoding="utf-8")
            try:
                (root / "linked.txt").symlink_to(private)
            except OSError as error:
                self.skipTest(f"Symbolic link creation unavailable: {error}")
            result = write_archive(root, ["linked.txt"], parent / "release.zip", "test-revision")
            self.assertEqual(result["file_count"], 0)
            self.assertEqual(result["excluded_candidates"], ["linked.txt"])


if __name__ == "__main__":
    unittest.main()

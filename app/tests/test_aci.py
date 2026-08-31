"""
Unit Tests für das ACI (Agent-Computer Interface) Toolkit von L.I.A.R.A.
"""
import unittest
import tempfile
import os
from pathlib import Path

from services.aci.file_navigator import view_file, grep_search, find_files
from services.aci.code_editor import replace_chunk, create_file, delete_file
from services.aci.code_validator import validate_python_syntax
from services.aci.patch_builder import generate_unified_diff, create_patch_summary


class TestACIToolkit(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        
        # Test-Dateien anlegen
        (self.tmp_path / "main.py").write_text(
            "import os\n\ndef add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n",
            encoding="utf-8"
        )
        (self.tmp_path / "helper.py").write_text(
            "def greet(name):\n    return f'Hello, {name}'\n",
            encoding="utf-8"
        )
        (self.tmp_path / "empty.txt").write_text("", encoding="utf-8")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_view_file(self):
        target = self.tmp_path / "main.py"
        
        # 1. Normale Anzeige mit Zeilenbereich
        res = view_file(path=target, start_line=1, end_line=3)
        self.assertTrue(res["success"])
        self.assertEqual(res["start_line"], 1)
        self.assertEqual(res["end_line"], 3)
        self.assertEqual(res["total_lines"], 7)
        self.assertIn("1 | import os", res["content"])
        self.assertIn("3 | def add(a, b):", res["content"])

        # 2. Leere Datei
        empty_target = self.tmp_path / "empty.txt"
        empty_res = view_file(path=empty_target)
        self.assertTrue(empty_res["success"])
        self.assertEqual(empty_res["total_lines"], 0)

        # 3. Nicht-existierende Datei
        non_existent = self.tmp_path / "does_not_exist.py"
        err_res = view_file(path=non_existent)
        self.assertFalse(err_res["success"])
        self.assertIn("nicht gefunden", err_res["error"])

    def test_find_and_grep_search(self):
        # 1. find_files
        find_res = find_files(root_dir=self.tmp_path, pattern="*.py")
        self.assertTrue(find_res["success"])
        self.assertIn("main.py", find_res["files"])
        self.assertIn("helper.py", find_res["files"])

        # 2. grep_search nach Funktionsdefinition
        grep_res = grep_search(query="def add", root_dir=self.tmp_path)
        self.assertTrue(grep_res["success"])
        self.assertEqual(grep_res["count"], 1)
        self.assertEqual(grep_res["matches"][0]["file"], "main.py")
        self.assertEqual(grep_res["matches"][0]["line_number"], 3)

    def test_validate_python_syntax(self):
        valid_code = "def test_func():\n    return 42\n"
        res_valid = validate_python_syntax(valid_code)
        self.assertTrue(res_valid["valid"])
        self.assertIsNone(res_valid["error"])

        invalid_code = "def test_func(\n    return 42\n"
        res_invalid = validate_python_syntax(invalid_code)
        self.assertFalse(res_invalid["valid"])
        self.assertIn("SyntaxError", res_invalid["error"])

    def test_replace_chunk(self):
        target = self.tmp_path / "main.py"

        # 1. Ziel nicht gefunden
        err_not_found = replace_chunk(
            target_content="def non_existing():\n    pass",
            replacement_content="def foo():\n    pass",
            path=target
        )
        self.assertFalse(err_not_found["success"])
        self.assertIn("nicht exakt gefunden", err_not_found["error"])

        # 2. Syntax-Fehler im Ersatzcode abfangen
        err_syntax = replace_chunk(
            target_content="def sub(a, b):\n    return a - b",
            replacement_content="def sub(a, b\n    return a - b", # Fehlende Klammer
            path=target
        )
        self.assertFalse(err_syntax["success"])
        self.assertIn("SyntaxError", err_syntax["error"])
        
        # Datei darf unverändert sein
        self.assertIn("def sub(a, b):\n    return a - b", target.read_text(encoding="utf-8"))

        # 3. Gültige Ersetzung
        success_res = replace_chunk(
            target_content="def sub(a, b):\n    return a - b",
            replacement_content="def sub(a, b):\n    # Berechne Differenz\n    return a - b",
            path=target
        )
        self.assertTrue(success_res["success"])
        updated_content = target.read_text(encoding="utf-8")
        self.assertIn("# Berechne Differenz", updated_content)

    def test_patch_builder(self):
        orig = "def hello():\n    print('hi')\n"
        mod = "def hello():\n    print('hello world')\n"
        diff = generate_unified_diff(orig, mod, from_file="a/test.py", to_file="b/test.py")
        self.assertIn("--- a/test.py", diff)
        self.assertIn("+++ b/test.py", diff)
        self.assertIn("-    print('hi')", diff)
        self.assertIn("+    print('hello world')", diff)

        summary = create_patch_summary([{"filename": "test.py", "original": orig, "modified": mod}])
        self.assertEqual(summary["files_changed"], 1)
        self.assertEqual(summary["additions"], 1)
        self.assertEqual(summary["deletions"], 1)


if __name__ == "__main__":
    unittest.main()

# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA Corporation
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"


class SkillDocsTests(unittest.TestCase):
    def skill_files(self):
        return sorted(SKILLS_ROOT.glob("*/SKILL.md"))

    def test_skill_frontmatter_names_match_directories(self):
        for path in self.skill_files():
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                text = path.read_text()
                self.assertTrue(text.startswith("---\n"), "missing YAML frontmatter")
                end = text.find("\n---\n", 4)
                self.assertNotEqual(end, -1, "unterminated YAML frontmatter")
                frontmatter = text[4:end]
                fields = dict(re.findall(r"^(name|description):\s*(.*)$", frontmatter, re.MULTILINE))
                self.assertEqual(path.parent.name, fields.get("name"))
                self.assertTrue(fields.get("description"))

    def test_skill_indexes_cover_all_skills(self):
        skills = [path.parent.name for path in self.skill_files()]
        root_readme = (REPO_ROOT / "README.md").read_text()
        skills_readme = (SKILLS_ROOT / "README.md").read_text()

        for skill in skills:
            with self.subTest(skill=skill):
                self.assertIn(f".agents/skills/{skill}/SKILL.md", root_readme)
                self.assertIn(f"[{skill}]({skill}/)", skills_readme)

    def test_markdown_links_resolve(self):
        files = [
            REPO_ROOT / "README.md",
            SKILLS_ROOT / "README.md",
            *self.skill_files(),
        ]
        for path in files:
            text = path.read_text()
            for _, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                target = target.split("#", 1)[0]
                if not target:
                    continue
                with self.subTest(path=path.relative_to(REPO_ROOT), target=target):
                    self.assertTrue((path.parent / target).exists())

    def test_no_user_absolute_paths_in_skill_docs(self):
        stale_path = re.compile(r"/Users/|/home/abaillet")
        for path in [REPO_ROOT / "README.md", *self.skill_files()]:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertIsNone(stale_path.search(path.read_text()))

    def test_profiling_guide_alignment_markers(self):
        expected_markers = {
            ".agents/skills/profiling/SKILL.md": [
                "TRACY_PORT",
                "carb_sdk_plugins",
                "0.11.1+nv1",
            ],
            ".agents/skills/install-profilers/SKILL.md": [
                "carb_sdk_plugins",
                "all-deps.packman.xml",
                "0.11.1+nv1",
            ],
            ".agents/skills/nsys-analyze/SKILL.md": [
                "total_time",
                "total_ns",
                "Normalize the column names",
            ],
            ".agents/skills/profiling-api/SKILL.md": [
                "kCaptureMaskProfiler",
                "is_python_profiling_enabled",
                "mask `0`",
            ],
            ".agents/skills/tracy-memory/SKILL.md": [
                "TRACY_PORT",
                "LD_PRELOAD",
                "TRACY_USE_LIB_UNWIND_FOR_BT",
            ],
            ".agents/skills/nvtx-python/SKILL.md": [
                'NVTX_SKILL_DIR="${NVTX_SKILL_DIR:-$PWD/.agents/skills/nvtx-python}"',
                "sitecustomize.py",
                "PYTHONPATH",
            ],
        }

        for rel_path, markers in expected_markers.items():
            text = (REPO_ROOT / rel_path).read_text()
            for marker in markers:
                with self.subTest(path=rel_path, marker=marker):
                    self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()

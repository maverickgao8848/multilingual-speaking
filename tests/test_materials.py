from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "materials.py"
SPEC = importlib.util.spec_from_file_location("materials", MODULE_PATH)
assert SPEC and SPEC.loader
materials = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(materials)


class MaterialsTests(unittest.TestCase):
    def test_all_thirty_a1_packs_resolve(self):
        for language in ("es", "fr", "de", "ja", "ko"):
            for scene in ("cafe-order", "directions-transit", "doctor-visit", "introductions", "shopping", "making-plans"):
                with self.subTest(language=language, scene=scene):
                    card = materials.build_card(language, scene, "A1", 10)
                    self.assertEqual(card["language"], language)
                    self.assertEqual(card["scene"], scene)
                    self.assertEqual(len(card["keywords"]), 2)
                    self.assertEqual(len(card["phrases"]), 2)
                    self.assertEqual(len(card["sentence_patterns"]), 2)
                    self.assertEqual(len(card["story_nodes"]), 4)
                    self.assertTrue(card["source_refs"])

    def test_duration_selects_one_two_four_or_six_patterns(self):
        expected = {5: 1, 10: 2, 20: 4, 40: 6}
        for duration, count in expected.items():
            with self.subTest(duration=duration):
                card = materials.build_card("fr", "shopping", "A1", duration)
                self.assertEqual(len(card["sentence_patterns"]), count)

    def test_preview_plan_scales_vocabulary_more_than_phrases_or_patterns(self):
        expected = {
            5: (15, 3, 2),
            10: (20, 5, 3),
            20: (30, 8, 5),
            40: (40, 12, 8),
        }
        for duration, counts in expected.items():
            with self.subTest(duration=duration):
                card = materials.build_card("fr", "cafe", "A1", duration)
                plan = card["preview_plan"]
                self.assertEqual(
                    (plan["keyword_count"], plan["phrase_count"], plan["sentence_pattern_count"]),
                    counts,
                )
                self.assertGreater(plan["keyword_count"], plan["phrase_count"])
                self.assertIn("session-original", plan["supplement_policy"])

    def test_chinese_aliases_and_unicode_survive(self):
        japanese = materials.build_card("日语", "问路", "a1", 20)
        korean = materials.build_card("韩语", "看医生", "a1", 10)
        self.assertIn("駅", japanese["keywords"][0]["surface"])
        self.assertEqual(korean["sentence_patterns"][0]["surface"], "목이 아파요.")

    def test_japanese_markdown_hides_romanization_by_default(self):
        card = materials.build_card("ja", "directions", "A1", 10)
        hidden = materials.render_markdown(card, False)
        shown = materials.render_markdown(card, True)
        self.assertNotIn("massugu", hidden)
        self.assertIn("massugu", shown)

    def test_korean_mappings_are_explicitly_partial(self):
        for scene in ("cafe", "directions", "doctor", "plans"):
            card = materials.build_card("ko", scene, "A1", 10)
            self.assertEqual(card["source_boundary"], "partial")
            self.assertTrue(all(mapping.get("coverage") for mapping in card["source_mappings"]))

    def test_new_scene_aliases_resolve(self):
        self.assertEqual(materials.build_card("西班牙语", "自我介绍", "A1", 10)["scene"], "introductions")
        self.assertEqual(materials.build_card("de", "购物", "A1", 10)["scene"], "shopping")
        self.assertEqual(materials.build_card("ja", "约时间", "A1", 10)["scene"], "making-plans")

    def test_unsupported_level_fails_instead_of_falling_back(self):
        with self.assertRaisesRegex(ValueError, "no audited A1 pack"):
            materials.build_card("es", "cafe", "B1", 10)

    def test_topic_catalog_distinguishes_ready_and_on_demand(self):
        catalog = materials.list_topics("法语")
        ready = [topic for topic in catalog["topics"] if topic["status"] == "audited_ready"]
        on_demand = [topic for topic in catalog["topics"] if topic["status"] == "on_demand"]
        self.assertEqual(catalog["language"], "fr")
        self.assertEqual(set(catalog["languages"]), {"es", "fr", "de", "ja", "ko"})
        self.assertEqual(len(ready), 6)
        self.assertEqual(len(on_demand), 20)
        self.assertTrue(all(topic.get("material_scene") for topic in ready))
        self.assertTrue(all(not topic.get("material_scene") for topic in on_demand))

    def test_runtime_curriculum_is_inside_skill_folder(self):
        root = materials.curriculum_root().resolve()
        skill_root = materials.SKILL_ROOT.resolve()
        self.assertEqual(root.parent, skill_root)
        self.assertEqual(root.name, "curriculum")

    def test_topic_markdown_is_an_explicit_status_table(self):
        table = materials.render_topic_table(materials.list_topics("ja"))
        self.assertIn("| # | 主题 | 准备状态 | 使用说明 |", table)
        self.assertIn("| 已备课 |", table)
        self.assertIn("| 需现场准备 |", table)
        self.assertIn("日语可选口语主题", table)


if __name__ == "__main__":
    unittest.main()

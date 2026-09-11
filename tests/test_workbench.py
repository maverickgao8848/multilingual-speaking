from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import urlopen


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("multilingual_workbench", SCRIPT_DIR / "workbench.py")
assert SPEC and SPEC.loader
workbench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workbench)


def session(**changes):
    payload = {
        "id": "20260910-193000-fr-cafe",
        "created_at": "2026-09-10T19:30:00+08:00",
        "language": "fr",
        "scene": "cafe-order",
        "duration_minutes": 10,
        "level": "A1",
        "support_mode": "guided",
        "interaction_mode": "text",
        "targets": [
            {
                "material_id": "fr.cafe.pattern.01",
                "status": "mastered",
                "support": "independent",
                "evidence": "Je voudrais un café, s'il vous plaît.",
            }
        ],
        "pronunciation": {"status": "not_observed", "notes": []},
    }
    payload.update(changes)
    return payload


class WorkbenchTests(unittest.TestCase):
    def test_canonical_session_restores_content_and_provenance(self):
        payload = session()
        payload["targets"][0]["surface"] = "wrong text"
        normalized = workbench.canonical_session(payload)
        target = normalized["targets"][0]
        self.assertEqual(target["surface"], "Je voudrais un café, s'il vous plaît.")
        self.assertEqual(target["adaptation"], "normalized")
        self.assertTrue(target["source_refs"])
        self.assertEqual(normalized["provenance"], "audited_curriculum")

    def test_cross_language_material_is_rejected(self):
        payload = session(language="de")
        with self.assertRaisesRegex(ValueError, "does not belong"):
            workbench.canonical_session(payload)

    def test_text_session_cannot_claim_pronunciation_observation(self):
        payload = session()
        payload["pronunciation"] = {"status": "observed", "evidence_mode": "live_audio", "notes": ["liaison was clear"]}
        with self.assertRaisesRegex(ValueError, "heard audio evidence"):
            workbench.canonical_session(payload)

    def test_voice_session_can_archive_heard_pronunciation_evidence(self):
        payload = session(interaction_mode="voice")
        payload["pronunciation"] = {"status": "observed", "evidence_mode": "live_audio", "notes": ["vous avez liaison needs a retry"]}
        normalized = workbench.canonical_session(payload)
        self.assertEqual(normalized["pronunciation"]["status"], "observed")
        self.assertEqual(normalized["interaction_mode"], "voice")

    def test_archive_is_idempotent_but_refuses_collision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "session.json"
            input_path.write_text(json.dumps(session(), ensure_ascii=False), encoding="utf-8")
            workbench.archive_session(root / "data", input_path)
            workbench.archive_session(root / "data", input_path)
            state = workbench.load_state(root / "data")
            self.assertEqual(len(state["sessions"]), 1)

            changed = session()
            changed["targets"][0]["status"] = "needs_review"
            input_path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "different data"):
                workbench.archive_session(root / "data", input_path)

    def test_dashboard_groups_language_and_scene(self):
        normalized = workbench.canonical_session(session())
        page = workbench.render_dashboard({"sessions": [normalized]})
        self.assertIn("法语", page)
        self.assertIn("咖啡店点单", page)
        self.assertIn("已掌握：1/1", page)

    def test_catalog_has_five_languages_and_six_scenes(self):
        catalog = workbench.catalog_payload()
        self.assertEqual(len(catalog["languages"]), 5)
        self.assertEqual(len(catalog["scenes"]), 6)

    def test_recommendations_use_latest_observation_and_explain_priority(self):
        first = workbench.canonical_session(session())
        first["targets"][0]["status"] = "needs_review"
        first["targets"][0]["support"] = "model"
        second_payload = session(id="20260910-200000-fr-cafe", created_at="2026-09-10T20:00:00+08:00")
        second_payload["targets"][0]["status"] = "developing"
        second_payload["targets"][0]["support"] = "form_prompt"
        second = workbench.canonical_session(second_payload)
        recommendation = workbench.recommendation_payload({"preferences": workbench.empty_state()["preferences"], "sessions": [first, second]}, "fr")
        queued = recommendation["review_queue"][0]
        self.assertEqual(queued["status"], "developing")
        self.assertEqual(queued["attempts"], 2)
        self.assertIn("需要形式提示", queued["reasons"])
        self.assertEqual(recommendation["next_lesson"]["type"], "review")
        self.assertEqual(recommendation["next_lesson"]["scene"], "cafe-order")

    def test_mastered_latest_observation_leaves_review_queue(self):
        older_payload = session(id="older", created_at="2026-09-09T20:00:00+08:00")
        older_payload["targets"][0]["status"] = "needs_review"
        older = workbench.canonical_session(older_payload)
        mastered = workbench.canonical_session(session())
        recommendation = workbench.recommendation_payload({"preferences": workbench.empty_state()["preferences"], "sessions": [older, mastered]}, "fr")
        self.assertEqual(recommendation["review_queue"], [])
        self.assertEqual(recommendation["next_lesson"]["type"], "new_scene")

    def test_empty_history_recommends_selected_starter_scene(self):
        state = workbench.empty_state()
        state["preferences"].update({"language": "ja", "scene": "shopping"})
        recommendation = workbench.recommendation_payload(state)
        self.assertEqual(recommendation["next_lesson"]["pack_id"], "ja.shopping.a1")
        self.assertEqual(recommendation["next_lesson"]["type"], "new_scene")

    def test_default_recommendation_uses_highest_priority_across_languages(self):
        payload = session(language="ja", scene="directions-transit")
        payload["targets"] = [{
            "material_id": "ja.directions.pattern.03",
            "status": "needs_review",
            "support": "model",
        }]
        state = workbench.empty_state()
        state["preferences"]["language"] = "fr"
        state["sessions"] = [workbench.canonical_session(payload)]
        recommendation = workbench.recommendation_payload(state)
        self.assertEqual(recommendation["next_lesson"]["language"], "ja")
        self.assertEqual(recommendation["next_lesson"]["review_target_ids"], ["ja.directions.pattern.03"])

    def test_local_api_serves_catalog_card_and_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary) / "data"
            workbench.init_workbench(data_dir)
            static_dir = Path(__file__).resolve().parents[1] / "assets" / "workbench"
            server = ThreadingHTTPServer(("127.0.0.1", 0), workbench.make_handler(data_dir, static_dir))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with urlopen(base + "/api/catalog") as response:
                    catalog = json.load(response)
                with urlopen(base + "/api/card?language=ja&scene=directions&duration=20") as response:
                    card = json.load(response)
                with urlopen(base + "/api/state") as response:
                    saved = json.load(response)
                with urlopen(base + "/api/recommendations?language=ja") as response:
                    recommendation = json.load(response)
                self.assertEqual(len(catalog["languages"]), 5)
                self.assertEqual(card["pack_id"], "ja.directions-transit.a1")
                self.assertEqual(len(card["sentence_patterns"]), 4)
                self.assertEqual(saved["sessions"], [])
                self.assertEqual(recommendation["next_lesson"]["language"], "ja")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

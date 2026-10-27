"""DEPI knowledge pack coverage and the 04B retrieval contract, checked against the repo files."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "kb"))
import depi_knowledge_pack as kp  # noqa: E402

WORKFLOW = ROOT / "infra" / "n8n" / "workflows" / "04B_knowledge_base_faq.json"
NODE = shutil.which("node")


@pytest.fixture(scope="module")
def pack():
    if not (kp.CATALOG.exists() and kp.INDUSTRY.exists()):
        pytest.skip("DEPI catalog sources (FAQs/Catal) are not present in this checkout")
    return kp.build()


def _node(name):
    wf = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    return next(n for n in wf["nodes"] if n["name"] == name)


def test_every_catalog_job_profile_is_in_the_pack_with_its_full_study_plan(pack):
    catalog = {**kp.parse_catalog(kp.CATALOG), **kp.parse_catalog(kp.INDUSTRY)}
    profiles = {e["pack_key"].split(":", 1)[1]: e for e in pack if e["pack_key"].startswith("profile:")}
    assert set(profiles) == set(kp.PROFILES)
    for name, e in profiles.items():
        for item in catalog[name]["curriculum"]:
            assert item in e["answer"] and item in e["answer_ar"], f"{name}: missing '{item}'"


def test_pack_entries_are_bilingual_unique_and_authoritative(pack):
    assert len({e["question"] for e in pack}) == len(pack)
    for e in pack:
        assert re.search(r"[؀-ۿ]", e["question_ar"] + e["answer_ar"]), e["pack_key"]
        assert e["answer"].strip() and e["keywords"] and e["keywords_ar"]
        assert (e["program"], e["retrieval_scope"]) == ("DEPI", "DEPI_AUTHORITATIVE")
        assert e["source_attribution"].startswith(kp.PACK)


def test_detector_topics_exist_in_the_pack(pack):
    code = _node("Program Detector & Query Normalizer")["parameters"]["jsCode"]
    topics = set(re.findall(r"\['((?:core|catalog)_[a-z_]+)'", code))
    assert topics and topics <= {e["category"] for e in pack}


def test_retrieval_query_binds_customer_text_instead_of_interpolating_it():
    params = _node("Query Bilingual Knowledge Base")["parameters"]
    assert "{{" not in params["query"]
    assert {"$1::text", "$2::text", "$3::text", "$4::text"} <= set(re.findall(r"\$\d::text", params["query"]))
    assert params["options"]["queryReplacement"].startswith("={{ [")


def _format(rows, topic=""):
    if NODE is None:
        pytest.skip("Node.js is required to execute n8n Code nodes")
    runner = r"""
const {code, items, refs} = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const $input = {first: () => ({json: items[0] || {}}), all: () => items.map(j => ({json: j}))};
const $ = (name) => ({first: () => ({json: refs[name] || {}})});
process.stdout.write(JSON.stringify(new Function('$input', '$', code)($input, $)[0].json));
"""
    detector = {"locale": "ar", "topic_category": topic, "customer_message": "q", "normalized_message": "q"}
    out = subprocess.run([NODE, "-e", runner], capture_output=True, text=True, encoding="utf-8", check=True,
                         input=json.dumps({"code": _node("Format RAG Knowledge Response")["parameters"]["jsCode"],
                                           "items": rows, "refs": {"Program Detector & Query Normalizer": detector}}))
    return json.loads(out.stdout)


def _row(**kw):
    base = {"program": "DEPI", "retrieval_scope": "DEPI_AUTHORITATIVE", "category": "catalog_profile",
            "answer_ar": "إجابة", "answer": "answer", "curated": True, "keyword_match_count": 1, "content_match_count": 1}
    return {**base, **kw}


def test_semantic_similarity_alone_never_answers():
    out = _format([_row(relevance_score=38, lexical_score=1, semantic_score=29)])
    assert out["action"] == "SAFE_DEFLECTION"


def test_clear_curated_match_is_answered_verbatim():
    out = _format([_row(relevance_score=66, lexical_score=20, semantic_score=38, answer_ar="DevOps"),
                   _row(relevance_score=51, lexical_score=14, semantic_score=29)])
    assert out["direct_answer"] is True and out["curated_answer"] == "DevOps"


def test_tied_curated_profiles_are_answered_together():
    out = _format([_row(relevance_score=61, lexical_score=20, semantic_score=33, answer_ar="SAP MM"),
                   _row(relevance_score=60.8, lexical_score=20, semantic_score=32.8, answer_ar="SAP FI")])
    assert out["direct_answer"] is True and out["curated_answer"] == "SAP MM\n\nSAP FI"


def _intent(message):
    if NODE is None:
        pytest.skip("Node.js is required to execute n8n Code nodes")
    wf = json.loads((ROOT / "infra/n8n/workflows/03_ai_intent_engine.json").read_text(encoding="utf-8"))
    code = next(n for n in wf["nodes"] if n["name"] == "Build Prompt Payload")["parameters"]["jsCode"]
    runner = r"""
const {code, item} = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const $input = {first: () => ({json: item})};
process.stdout.write(JSON.stringify(new Function('$input', code)($input)[0].json));
"""
    out = subprocess.run([NODE, "-e", runner], capture_output=True, text=True, encoding="utf-8", check=True,
                         input=json.dumps({"code": code, "item": {"customer_message": message}}))
    return json.loads(out.stdout)


@pytest.mark.parametrize("message", ["السلام عليكم", "شكرا جزيلا", "Hello!", "صباح الخير 🙏"])
def test_greetings_are_small_talk_without_the_llm(message):
    out = _intent(message)
    assert out.get("direct_bypass") is True and out["ai_output"]["intent"] == "general_support"


@pytest.mark.parametrize("message", ["عايز اعرف محتوى كورس DevOps", "هل فيه كورس SAP؟", "Is there a Power BI course?", "مدة التدريب كام شهر"])
def test_course_questions_route_to_the_knowledge_base(message):
    assert _intent(message)["ai_output"]["intent"] == "faq_query"


def test_uncurated_top_match_goes_to_grounded_generation():
    out = _format([_row(relevance_score=81, lexical_score=38, semantic_score=43, curated=False, category="live_chat")])
    assert out["action"] == "ANSWER" and out["direct_answer"] is False

from datetime import date,timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.course.catalog import AUDIO,BOOKS,LESSONS,VERSION,compare_ipa,grade,study_state,summary

client=TestClient(app)

def test_complete_catalog_and_public_keys():
    assert client.get("/demo/course").status_code==200
    catalog=client.get("/demo/course/catalog").json()
    assert len(set(i["id"] for i in catalog["lessons"]))==281
    assert sum("Review your last sound group"==v["title"] for v in LESSONS.values())==7
    for lesson in catalog["lessons"]:
        assert lesson["book"] in BOOKS and lesson["topics"]
        for phase in ("practice","review"):
            public=client.get("/demo/course/lesson/"+lesson["id"],params={"phase":phase}).json()
            assert len(public["exercises"])==len(LESSONS[lesson["id"]][phase])
            for item in public["exercises"]:
                assert "key" not in item and "feedback" not in item
                if item.get("audio"):assert item["audio"] in AUDIO and item["accent"] in ("en-US","en-GB")

def test_symbol_feedback_variants_and_context():
    ok,diff=compare_ipa("/sɪt/",["sit"])
    assert not ok and [(i["kind"],i["target"]) for i in diff]==[("equal","s"),("replace","i"),("equal","t")]
    for value,keys in [("/siːt/",["sit"]),("[si:t]",["sit"]),("rɛd",["ɹɛd"]),("g",["ɡ"]),("kɑt",["kɔt","kɑt"]),("a.b",["ab"]),("'fɪfti",["ˈfɪfti"])]:
        assert compare_ipa(value,keys)[0]
    assert "ɡ" in summary("use-26")["symbols"]
    for value,target,kind in [("st","sit","insert"),("siit","sit","delete"),("sɪt","sit","replace")]:
        assert kind in [i["kind"] for i in compare_ipa(value,[target])[1]]
    assert not compare_ipa("fəʊtəɡɹæfɪk",["ˌfoʊtəˈɡɹæfɪk"])[0]
    word=client.get("/demo/course/word",params={"word":"  MONDAY "}).json()
    assert word["available"]
    assert not client.get("/demo/course/word?word=uncatalogued").json()["available"]
    read=next(i for i in LESSONS["use-28"]["practice"] if i["kind"]=="ipa")
    review=next(i for i in LESSONS["use-28"]["review"] if i["kind"]=="ipa")
    assert read["context"]!=review["context"] and grade("use-28",read["id"],review["key"][0])["outcome"]=="retry"

def make_event(lid,item,day):
    answer=item.get("key","unavailable")
    payload={"version":VERSION,"lesson":lid,"exercise":item["id"],"attempt_id":str(uuid4()),"answer":answer[0] if isinstance(answer,list) else answer}
    r=client.post("/demo/course/grade",json=payload)
    assert r.status_code==200
    return {**r.json(),"day":day.isoformat()}

def test_two_lessons_review_and_resume():
    now=date(2026,11,24)
    history=[]
    for lid in ("ship-01","use-53"):
        assert study_state(history,now)["next"]==lid
        for item in LESSONS[lid]["practice"]:
            history.append(make_event(lid,item,now))
        assert lid in study_state(history,now)["completed"]
    state=study_state(history,now+timedelta(days=1))
    assert set(state["due"])=={"ship-01","use-53"}
    assert state["skills"]["Speaking"]["unavailable"]==4 and state["communication"]["correct"]>=2
    for item in LESSONS["ship-01"]["review"]:
        history.append(make_event("ship-01",item,now+timedelta(days=1)))
    done=study_state(history,now+timedelta(days=1))
    assert done["due"]==["use-53"] and done["reviewDates"]["ship-01"]=="2026-12-02"
    assert done["delayedFirstResponses"]["correct"]>0

def test_missing_and_stale_submissions():
    assert client.get("/demo/course/lesson/missing").status_code==404
    assert client.get("/demo/course/audio/missing").status_code==404
    assert client.get("/demo/assets/catalog.py").status_code==404
    base={"version":VERSION,"attempt_id":str(uuid4()),"lesson":"ship-01","exercise":"p1","answer":"made-up"}
    assert client.post("/demo/course/grade",json=base).status_code==422
    assert client.post("/demo/course/grade",json={**base,"version":"old"}).status_code==409


def test_review_uses_the_current_word_and_hides_listening_answer():
    lesson=client.get("/demo/course/lesson/ship-01?phase=review").json()
    listening=lesson["exercises"][0]
    assert "word" not in listening and "contrast" not in listening
    item=next(x for x in lesson["exercises"] if x["kind"]=="ipa")
    assert item["word"]=="peach" and "contrast" not in item
    result=grade("ship-01",item["id"],"pɪtʃ")
    assert [c["word"] for c in result["contrast"]]==["pitch","peach"]
    assert all(c["audio"] in AUDIO for c in result["contrast"])
    for item in LESSONS["ship-07"]["practice"]:
        if item["kind"]=="choice" and "word" in item:
            assert grade("ship-07",item["id"],item["key"])["word"]==item["word"]


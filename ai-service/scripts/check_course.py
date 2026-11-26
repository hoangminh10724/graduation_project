"""Verify that every curriculum row, private key and reference recording is deliverable."""
import argparse
from collections import Counter
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.course.catalog import AUDIO, BOOKS, LESSONS, ORDER, VERSION, grade, public_lesson, summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--decode-audio", action="store_true")
    args = parser.parse_args()
    rows = ["# WordSpeak curriculum coverage", "",
            f"Edition `{VERSION}`. Each source locator opens one playable lesson. The suggested previous lesson guides Today. Library access is immediate.",
            "", "The key column names the private answer record. Open the exercise in the Python catalog to inspect its accepted answers. Audio identifiers resolve at `/demo/course/audio/{id}`; recordings are synthesized. Review IDs are separate from practice IDs.",
            "", "| Source and locator | WordSpeak lesson and objective | Solo activity | Model audio IDs | Private key and review | Suggested previous |",
            "|---|---|---|---|---|---|"]
    assert Counter(v["book"] for v in LESSONS.values()) == {"ship":52,"use":66,"discovery":88,"classroom":74,"guide":1}
    for lid, lesson in LESSONS.items():
        refs = set()
        for phase in ("practice","review"):
            items=lesson[phase]
            assert items and len({x["id"] for x in items})==len(items)
            for item in items:
                if item.get("audio"):refs.add(item["audio"])
                refs.update(m["audio"] for m in item.get("models",[]))
                if "key" in item:
                    key=item["key"]
                    if item["kind"]=="choice":
                        assert len(set(item["options"]))==2 and key in item["options"],(lid,item)
                    assert grade(lid,item["id"],key[0] if isinstance(key,list) else key)["outcome"]=="correct"
            assert all("key" not in item for item in public_lesson(lid,phase)["exercises"])
        assert refs and refs<=AUDIO.keys()
        link=f'http://127.0.0.1:8013/demo/course?lesson={lid}'
        rows.append(f"| {BOOKS[lesson['book']]} {lesson['source']} | [{lid}]({link}) · {lesson['title']} | {lesson['goal']} | {', '.join(sorted(refs))} | `LESSONS[\"{lid}\"]` · p1–{lesson['practice'][-1]['id']}, r1–{lesson['review'][-1]['id']} | {summary(lid)['after'] or 'Start'} |")
    if args.decode_audio:
        sys.path.append(str(ROOT/"data/speech-tools"))
        import av
        import numpy as np
    if not args.skip_audio:
        for key in AUDIO:
            path=ROOT/"ai-service/app/course/audio"/(key+".mp3")
            assert path.stat().st_size>500, path
            if args.decode_audio:
                with av.open(str(path)) as container:
                    frames=list(container.decode(audio=0))
                    assert frames and any(np.max(np.abs(f.to_ndarray()))>.005 for f in frames),path
    output=ROOT/"docs/COURSE_COVERAGE.md"
    content="\n".join(rows)+"\n"
    if args.write:output.write_text(content,encoding="utf-8")
    else:assert output.read_text(encoding="utf-8")==content, "Regenerate the coverage table with --write"
    print(f"{len(LESSONS)} playable entries, {len(AUDIO)} audio references, edition {VERSION}")

if __name__=="__main__":
    main()

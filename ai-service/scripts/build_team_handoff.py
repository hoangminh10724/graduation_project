"""Package the speech-team overlay without replacing receiving-team infrastructure."""
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]
EXTRA = (
    "00-START-HERE.md", "docs/COURSE_COVERAGE.md", "docs/COURSE_HANDOFF.md",
    "docs/FRONTEND_COURSE_HANDOFF.md", "docs/BACKEND_COURSE_HANDOFF.md",
    "docs/integration/self-study-course.patch",
    "docs/integration/talk-transcript-timing.patch", "docs/integration/account-review-entry.patch",
    "docs/integration/account-practice-words.patch", "docs/integration/spoken-tutor.patch",
    "START_WORDSPEAK.cmd", "docs/openapi.yaml", "docs/CONVERSATION_HANDOFF.md",
    "docs/FEATURE_SPEC_UIUX_FRONTEND_VI.md", "docs/AMERICAN_SOUND_EXPANSION.md",
    "docs/UNDERHILL_REFERENCE.md", "docs/PHYSICAL_PRACTICE_VALIDATION.md",
    "docs/MVP_HANDOFF.md", "docs/TEN_SOUND_MVP.md", "docs/PRONUNCIATION_PRODUCT_STUDY.md",
    "data/prepared/summary.json", "data/prepared/new_collection_20261121/summary.json",
    "data/results/american_expansion/real_audio_summary.json", "reports/american_expansion/REPORT.md",
    "reports/pronunciation_baseline/REPORT.md", "reports/pronunciation_baseline/validation_checks.json",
    "reports/teacher_feedback_model_check/REPORT.md", "reports/conversation_handoff/live_phone_validation.json",
    "reports/conversation_handoff/transcription_validation.json",
    "reports/conversation_handoff/word_offer_validation.json",
    "reports/conversation_handoff/speech_model_hashes.json",
    "reports/conversation_handoff/qwen_tutor_review.json",
)


def main():
    names = set(EXTRA)
    service = ROOT / "ai-service"
    sys.path.insert(0,str(service))
    from app.course.catalog import AUDIO
    for path in (service / "app/course").iterdir():
        if path.suffix in {".tsv",".py"}: names.add(path.relative_to(ROOT).as_posix())
    names.update("ai-service/app/course/audio/"+key+".mp3" for key in AUDIO)
    names.update("ai-service/" + name for name in ("DEMO.md", "Dockerfile", "requirements.txt", "pytest.ini"))
    for directory, suffixes in (
        ("app", {".py"}),
        ("app/demo_static", {".css", ".html", ".js", ".mjs", ".svg"}),
        ("scripts", {".py", ".txt", ".html", ".md"}),
        ("tests", {".py", ".cjs", ".mjs"}),
    ):
        for path in (service / directory).iterdir():
            if path.is_file() and path.suffix in suffixes:
                names.add(path.relative_to(ROOT).as_posix())

    output = ROOT / "reports/conversation_handoff/WordSpeak-team-handoff.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=output.parent,suffix=".tmp",delete=False) as temp:
        staging=Path(temp.name)
    try:
        with ZipFile(staging, "w", ZIP_DEFLATED) as archive:
            for name in sorted(names):
                archive.write(ROOT / name, name)
        with ZipFile(staging) as archive:
            assert archive.testzip() is None
            assert all(archive.read(name) == (ROOT / name).read_bytes() for name in names)
        staging.replace(output)
    finally:
        staging.unlink(missing_ok=True)
    print(f"Verified {len(names)} files in {output}")


if __name__ == "__main__":
    main()

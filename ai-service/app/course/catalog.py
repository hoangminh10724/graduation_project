"""Original course content, public lesson views and server-side exercise keys."""
import csv
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).parent
BOOKS = {"ship": "Ship or Sheep?", "use": "English Pronunciation in Use",
         "discovery": "Sound Foundations · discovery", "classroom": "Sound Foundations · classroom"}
SKILLS = ("Listening", "IPA", "Speaking", "Meaning")
AUDIO = {}
LESSONS = {}


def rows(name):
    with (ROOT / (name + ".tsv")).open(encoding="utf-8") as source:
        return list(csv.reader((line for line in source if line.strip() and not line.startswith("#")), delimiter="|", quoting=csv.QUOTE_NONE))


def entry(field):
    word, keys = field.split(":")
    return word, keys.split(";")


def audio(line, accent="en-US", speaker=0):
    key = hashlib.sha256(f"{accent}/{speaker}/{line}".encode()).hexdigest()[:20]
    AUDIO[key] = (line, accent, speaker)
    return key


def plain(line):
    return re.sub(r"[*^!~]", "", line).strip()


def choice(skill, question, yes, no, explanation, clip=None):
    return dict(skill=skill, kind="choice", question=question, key=yes, options=[yes,no],
                feedback=explanation, audio=clip)


def ipa(word, keys, context, accent="en-US", clip=None):
    return dict(skill="IPA", kind="ipa", word=word, question=f"Write the broad IPA for “{word}”.",
                context=context, key=keys, feedback="Compare the marked symbols and try the word again.",
                audio=clip or audio(word,accent), accent=accent)


SOUNDS = {r[0]:r[1:] for r in rows("sounds")}
SYMBOL_PAIRS = dict(pair for left,right in (
    ("i","ɪ"),("ɛ","æ"),("ɑ","ʌ"),("ɔ","oʊ"),("u","ʊ"),("ɝ","ɚ"),("aɪ","eɪ"),("aʊ","ɔɪ"),
    ("p","b"),("t","d"),("k","ɡ"),("s","z"),("ʃ","ʒ"),("tʃ","dʒ"),("f","v"),("θ","ð"),
    ("l","ɹ"),("m","n"),("w","j"),("ɪɹ","ɛɹ")) for pair in ((left,right),(right,left)))
CONTEXTS = {r[0]:r[1:] for r in rows("contexts")}
EXCHANGES = {r[0]:r[1:] for r in rows("exchanges")}
SYMBOLS = list(dict.fromkeys([*SOUNDS, "ˈ", "ˌ", "ː", " ", "e", "r", "ɜ", "ɪə", "eə", "ʊə", "əʊ"]))


def exercise_set(resource, review=False):
    if resource in SOUNDS:
        base, other, fresh, foil, cue, uk = SOUNDS[resource]
        word, keys = entry(fresh if review else base)
        distractor = foil if review else other
        voice = int(review)
        position = keys[0].find(resource)
        target = resource
        if position < 0 and resource=="ɒ":
            target="ɑ"
            position=keys[0].index(target)
        location = "at the start" if position==0 else "at the end" if keys[0].endswith(target) else "inside the word"
        symbol_foil = SYMBOL_PAIRS.get(target,"n" if target=="ŋ" else "ɪ")
        line = f"The word was {word}." if review else f"I said {word}."
        items = [choice("Listening","Listen once. Which word did the speaker say?",word,distractor,cue,audio(line,speaker=voice)),
                 choice("IPA",f"Listen to {word}. Choose the symbol for the sound {location}.",target,symbol_foil,cue,audio(word,speaker=voice)),
                 choice("IPA",f"Which word fits /{keys[0]}/?",word,distractor,cue),
                 ipa(word,keys,"General American citation form.",clip=audio(word,speaker=voice))]
        items[-1]["contrast"]=[dict(word=w,audio=audio(w,speaker=voice)) for w in (distractor,word)]
        if not review and uk.split(";")[0]!=keys[0]:
            paired=SOUNDS.get(SYMBOL_PAIRS.get(target,"ɪ"),SOUNDS["ɪ"])
            british_foil=paired[-1].split(";")[0]
            items.append(choice("IPA",f"British reference: listen to “{word}”. Which is a British dictionary reading?",
                                "/"+uk.split(";")[0]+"/","/"+british_foil+"/",
                                "Compare this reading with the American production target.",audio(word,"en-GB")))
        for item in items:item["word"]=word
        return items,word,cue
    base,fresh,line_a,a,line_b,b,line_r,r,foil,scenario = CONTEXTS[resource]
    word,keys=entry(fresh if review else base)
    if review:
        items=[choice("Meaning","Listen to the new situation. Which interpretation fits?",r,foil,
                      "Replay and identify the detail that supports your answer.",audio(line_r,speaker=1))]
    else:
        items=[choice("Meaning","Listen to the delivery. What is the speaker doing?",a,b,
                      "Compare both readings and notice the word or movement that carries the message.",audio(line_a)),
               choice("Meaning","Listen to a second reading. What does it communicate?",b,a,
                      "Listen for the detail that changed.",audio(line_b))]
    context=plain(line_r if review else line_a)
    if resource=="stress":
        context="Please record our rehearsal." if review else "Keep a record of today's meeting."
    if resource=="weak":
        context="Give it to Lee." if review else "I can drive."
    if resource=="aux":
        context="I could take the train." if review else "We should take the bus."
    if resource=="pronouns":
        context="Give them the map." if review else "Give her the ticket."
    clip=audio(context,speaker=int(review)) if resource in ("stress","weak","pronouns","aux") else audio(word,speaker=int(review))
    items.append(ipa(word,keys,context,clip=clip))
    return items,word,scenario


def build(book,number,title,resources,task,question,answer,foil,stage=""):
    lid=f"{book}-{number}"
    practice=[]; reviews=[]; symbols=[]; focus=""
    for resource in resources:
        items,word,cue=exercise_set(resource)
        practice.extend(items)
        reviews.extend(exercise_set(resource,True)[0])
        if resource in SOUNDS:
            symbols.append(resource)
        if not focus:
            focus=word
    practice.append(choice("Meaning",question,answer,foil,task))
    scenario=CONTEXTS[next((k for k in resources if k in CONTEXTS),"invite")][-1]
    if all(k in SOUNDS for k in resources):
        scenario=f"A friend misheard “{focus}”. Use it in a complete message and clarify the detail."
        # Start situated listening in the very first sound lesson.
        practice.insert(1,exercise_set("invite")[0][0])
    if lid=="use-53":
        practice.insert(0,choice("Listening","The host repeats the reservation. How many places did you hear?",
            "Fifteen","Fifty","Listen to the final stressed syllable in fifteen.",audio("The reservation is for fifteen.")))
    if lid=="ship-01":
        scenario="Your friend heard sit. Ask for a seat in your own words, then clarify what you need."
    contexts=[CONTEXTS[k] for k in resources if k in CONTEXTS]
    if contexts:
        first=contexts[0]
        model=[dict(line=plain(first[i]),marked=first[i],intention=first[i+1],audio=audio(first[i])) for i in (2,4)]
        for index, item in enumerate(model):
            raw=first[2+index*2]
            beats=re.findall(r"\*([A-Za-z]+)\*",raw)
            expected=" ".join(re.findall(r"[a-z']+",plain(raw).lower()))
            if len(beats)==1 and len(expected.split())>1 and expected.split().count(beats[0].lower())==1:
                item["assessment"]=dict(id="prominence",variant=beats[0].lower(),expected=expected)
            elif expected=="really":
                item["assessment"]=dict(id="intonation",variant="rise" if "^" in raw else "fall",expected=expected)
    else:
        model=[dict(line=entry(SOUNDS[k][0])[0],intention=SOUNDS[k][4],audio=audio(entry(SOUNDS[k][0])[0])) for k in resources]
    if lid=="ship-01":
        model.append(dict(line="sit",intention="Relax the vowel and keep the consonants.",audio=audio("sit")))
    dialogue=next((k for k in resources if k in EXCHANGES),"invite")
    situation,reply,alternative=EXCHANGES[dialogue]
    practice.append(choice("Meaning","Choose a reply for this situation: "+situation,reply,alternative,
        "Check which reply gives this listener the information or action they need."))
    practice.append(dict(kind="record",skill="Speaking",question=task,focus=focus,feedback="Replay, change one feature, then compare both takes."))
    practice[-1]["models"]=model
    practice.append(dict(kind="reply",skill="Speaking",question=scenario,focus=focus,feedback="Listen for your intended detail. You can clarify it in a second take."))
    if lid in ("use-53","ship-01"):
        booking=lid=="use-53"
        practice.append(choice("Meaning","Your partner repeats this back. Did they get your request?",
            "Yes, they recovered the requested detail.","No, I still need to correct it.",
            "Compare the repeated detail with the original request.",audio("Right, fifteen guests." if booking else "You need a seat.",speaker=1)))
        reviews.append(dict(kind="reply",skill="Speaking",question="Correct a delivery of thirty cups to thirteen cups." if booking else "A shop assistant heard pitch. Tell them which fruit you want.",focus="thirteen" if booking else "peach",feedback="Replay the correction. Which detail can a listener recover?"))
    elif book in ("classroom","discovery","use"):
        fresh=exercise_set(resources[0],True)[1]
        reviews.append(dict(kind="record",skill="Speaking",focus=fresh,
            question=f"Apply the lesson to a new example using “{fresh}”. {task} Then compare your first and second versions.",
            feedback="Replay the new example and check the feature named in the lesson goal."))
    for prefix,items in (("p",practice),("r",reviews)):
        for i,item in enumerate(items):
            item["id"]=f"{prefix}{i+1}"
            if item["kind"]=="choice":
                random.Random(lid+item["id"]).shuffle(item["options"])
    LESSONS[lid]=dict(id=lid,book=book,source=number,title=title,goal=task,focus=focus,
                      symbols=symbols,resources=resources,stage=stage or book,
                      practice=practice,review=reviews)


block=[]
for i,(key,) in enumerate(rows("ship"),1):
    if key=="review":
        build("ship",f"{i:02}","Review your last sound group",block[:],"Try the words in this group from memory, then replay the least certain one.",
              "After a difficult item, what is the best check?","Listen to a fresh word with that sound","Count how many buttons you tapped")
        block=[]
    else:
        base,other,_,_,cue,_=SOUNDS[key]
        word=entry(base)[0]
        build("ship",f"{i:02}",f"{word.capitalize()} · explore /{key}/",[key],cue,
              f"What movement can you explore for “{word}”?",cue,"Hold every part of the mouth rigid.")
        block.append(key)
for book in ("use","discovery","classroom"):
    for i,(refs,title,task,q,a,b) in enumerate(rows(book),1):
        source=f"D{i-60}" if book=="use" and i>60 else f"{i:02}"
        build(book,source,title,refs.split(","),task,q,a,b)

build("ship","A","Starting check · hearing and notation",["i","ɪ","s","z","booking"],
      "Listen before looking at hints. Use your separate skill results to choose what to practise.",
      "Which result tells you about perception?","Selecting a word from unfamiliar audio","Counting recorded attempts")
build("ship","B","Starting check · spoken production",["clusters","longstress","group"],
      "Record a short request, replay it and identify one feature to practise. A listener is optional.",
      "Which evidence supports listener understanding?","The listener recovered the intended detail","The app created an audio file")

BOOKS["guide"]="WordSpeak starting point"
build("guide","start","Find my starting point",["i","booking"],"Sample listening, IPA and message interpretation, then choose where to start.",
      "Which skill do you want to try?","Interpret the message","Count the letters")
start=LESSONS["guide-start"]
listen,_,read,write=exercise_set("ɪ",True)[0][:4]
meaning=exercise_set("booking",True)[0][0]
start["practice"]=[listen,read,write,meaning,dict(kind="record",skill="Speaking",question="Optional: clarify a number that someone misheard.",focus="fifteen",feedback="Save a speaking attempt or skip it.")]
for i,item in enumerate(start["practice"],1):
    item["id"]=f"p{i}"
    if item["kind"]=="choice":random.Random("placement"+str(i)).shuffle(item["options"])

PATH_START=["ship-01","use-53","ship-02","use-25","use-26","use-27","discovery-03","use-22","use-38","use-43","classroom-69"]
ORDER=list(PATH_START)
# Interleave strands throughout the path, retaining source order within each.
for index in range(1,89):
    for book in ("ship","use","discovery","classroom"):
        lid=f"{book}-{index:02}"
        if lid in LESSONS and lid not in ORDER:
            ORDER.append(lid)
ORDER.extend(k for k in LESSONS if k not in ORDER)
LESSON_VERSIONS={lid:hashlib.sha256(json.dumps(lesson,sort_keys=True).encode()).hexdigest()[:12]
                 for lid,lesson in LESSONS.items()}
VERSION="1."+hashlib.sha256((json.dumps(LESSON_VERSIONS,sort_keys=True)+"grading-1").encode()).hexdigest()[:10]
PUBLIC_FIELDS=("id","book","source","title","goal","focus","symbols","stage")


def summary(lid):
    lesson=LESSONS[lid]
    info={k:lesson[k] for k in PUBLIC_FIELDS}
    info["skills"]=sorted(set(item["skill"] for item in lesson["practice"]))
    info["topics"]=(["Listening and articulation","IPA literacy"] if any(r in SOUNDS for r in lesson["resources"]) else [])
    if any(r in CONTEXTS for r in lesson["resources"]):
        info["topics"].extend(["Intonation and fluency","Conversational intelligibility"])
    info["symbols"]=list(dict.fromkeys([*info["symbols"],*(s for item in lesson["practice"] if item["kind"]=="ipa"
                             for s in units(item["key"][0]) if s in SYMBOLS)]))
    pos=ORDER.index(lid)
    info["after"]=ORDER[pos-1] if pos and lid!="guide-start" else None
    info["version"]=VERSION
    return info


def public_lesson(lid,phase):
    items=LESSONS[lid][phase]
    exercises=[{k:v for k,v in item.items() if k not in ("key","feedback","contrast") and
                not (k=="word" and item["kind"]=="choice")} for item in items]
    for item in exercises:
        if item.get("audio"):item["accent"]=AUDIO[item["audio"]][1]
    return {**summary(lid),"phase":phase,"exercises":exercises}


UNITS=sorted({"tʃ","dʒ","eɪ","aɪ","ɔɪ","aʊ","oʊ","ɪə","eə","ʊə","əʊ"},key=len,reverse=True)
def units(value):
    s=unicodedata.normalize("NFC",value.strip().strip("/[]")).replace("g","ɡ").replace("r","ɹ").replace("͡","").replace(":","ː").replace("'","ˈ")
    s=re.sub(r"([iuɑɔɝ])ː",r"\1",s)
    s=s.replace(".","").replace(" ","")
    return re.findall("|".join(UNITS)+r"|.",s)


def compare_ipa(value,keys):
    proposed=units(value)
    versions=[units(k) for k in keys]
    if all("ˈ" not in k and "ˌ" not in k for k in keys):
        proposed=[s for s in proposed if s not in ("ˈ","ˌ")]
    best=max(versions,key=lambda t:SequenceMatcher(None,proposed,t,autojunk=False).ratio())
    matcher=SequenceMatcher(None,proposed,best,autojunk=False)
    parts=[dict(kind=op,entered="".join(proposed[a:b]),target="".join(best[c:d]))
           for op,a,b,c,d in matcher.get_opcodes()]
    return proposed==best,parts


def grade(lid,exercise,value):
    item=next((i for group in ("practice","review") for i in LESSONS[lid][group] if i["id"]==exercise),None)
    if not item: raise KeyError(exercise)
    result=dict(skill=item["skill"],kind=item["kind"],feedback=item["feedback"])
    if item["kind"] in ("record","reply"):
        if item["kind"]=="reply" and value in ("recorded:listener_recovered","recorded:listener_repair"):
            return {**result,"outcome":"recorded","listener":value.split(":")[1]}
        if value not in ("recorded","unavailable"): raise ValueError("Unknown recording outcome")
        return {**result,"outcome":value}
    if item["kind"]=="ipa":
        correct,diff=compare_ipa(value,item["key"])
        result.update(diff=diff,reference=item["key"])
        if not correct and "contrast" in item:result["contrast"]=item["contrast"]
    else:
        if value not in item["options"]:raise ValueError("Choose one of the displayed answers")
        correct=value==item["key"]
        result["reference"]=item["key"]
    if item.get("word"):result["word"]=item["word"]
    return {**result,"outcome":"correct" if correct else "retry"}


def study_state(events,today=None):
    today=today or date.today()
    completed=set();counts={s:Counter() for s in SKILLS}
    seen={};next_review={};last_review={};placement={};last_practice=None
    first_review={};communication=Counter();listeners=Counter()
    active_days=set()
    for event in events:
        lid=event["lesson"]
        if lid not in LESSONS:continue
        if event.get("version")!=VERSION and event.get("lesson_version")!=LESSON_VERSIONS[lid]:continue
        stamp=date.fromisoformat(event["day"])
        if not event["exercise"]:continue
        prefix=event["exercise"][0]
        if prefix not in ("p","r"):continue
        item=next((x for x in LESSONS[lid]["practice" if prefix=="p" else "review"] if x["id"]==event["exercise"]),None)
        if item is None or item["skill"]!=event["skill"]:continue
        active_days.add(stamp)
        counts[event["skill"]][event["outcome"]]+=1
        if item["kind"]=="reply" and event.get("listener") in ("listener_recovered","listener_repair"):
            listeners[event["listener"]]+=1
        if item.get("question","").startswith(("Your partner repeats","Choose a reply for this situation")):
            communication[event["outcome"]]+=1
        if prefix=="r" and (lid not in next_review or stamp<next_review[lid]):continue
        if prefix=="r" and item["kind"] in ("ipa","choice"):
            first_review.setdefault((lid,event["exercise"]),event["outcome"])
        if lid=="guide-start":placement.setdefault(event["exercise"],event["outcome"])
        if prefix=="p" and lid!="guide-start":last_practice=lid
        if event["outcome"] in ("correct","recorded","unavailable"):
            if prefix=="r" and stamp<next_review.get(lid,stamp):continue
            passed=seen.setdefault((lid,prefix),set())
            passed.add(event["exercise"])
            if prefix=="p" and lid not in completed and len(passed)==len(LESSONS[lid]["practice"]):
                completed.add(lid)
                if lid!="guide-start":next_review[lid]=stamp+timedelta(days=1)
            if prefix=="r" and lid in completed and len(passed)==len(LESSONS[lid]["review"]):
                last_review[lid]=stamp;next_review[lid]=stamp+timedelta(days=7);passed.clear()
    due=sorted((k for k,d in next_review.items() if d<=today),key=next_review.get)
    recommendations={skill:lid for index,skill,lid in (("p1","Listening","ship-02"),("p2","IPA reading","use-D1"),
                       ("p3","IPA writing","classroom-23"),("p4","Meaning","use-53")) if placement.get(index)=="retry"}
    suggested=next((k for k in recommendations.values() if k not in completed),None)
    if last_practice and last_practice not in completed:suggested=last_practice
    if placement and "guide-start" not in completed and not last_practice:suggested="guide-start"
    suggested=suggested or next((k for k in ORDER if k not in completed and k!="guide-start"),ORDER[0])
    streak=0
    cursor=today if today in active_days else (today-timedelta(days=1) if (today-timedelta(days=1)) in active_days else None)
    while cursor and cursor in active_days:
        streak+=1
        cursor-=timedelta(days=1)
    return dict(completed=[k for k in ORDER if k in completed],due=due,reviewDates={k:d.isoformat() for k,d in next_review.items()},
                reviewed=list(last_review),next=due[0] if due else suggested,phase="review" if due else "practice",
                doneItems={f"{k}/{p}":sorted(v) for (k,p),v in seen.items()},recommendations=recommendations,
                placement=placement,communication=communication,listeners=listeners,delayedFirstResponses=Counter(first_review.values()),skills=counts,streak=streak,version=VERSION)


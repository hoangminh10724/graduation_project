"""Synthetic decoded-label fixtures for browser behavior, not accuracy results."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ai-service'))
from app.pronunciation_demo import interpret_live
from app.sound_catalog import PROMPTS

CASES={
    'diphthong_difference':('day',['d','aɪ'],.9),
    'steady_for_glide':('day',['d','ɛ'],.9),
    'nasal_difference':('man',['b','æ','n'],.9),
    'medial_difference':('vision',['v','ɪ','s','ə','n'],.9),
    'ending_difference':('sing',['s','ɪ','n'],.9),
    'extra_ending':('sing',['s','ɪ','ŋ','ɡ'],.9),
    'accepted_merger':('caught',['k','ɑ','t'],.9),
    'r_stress_unknown':('bird',['b','ɚ','d'],.9),
    'weak_affricate':('chin',['d','ʒ','ɪ','n'],.9),
}
def main():
    out={}
    for key,(prompt,phones,peak) in CASES.items():
        pred={'predicted_phones':phones,'spans':[{'phone':p,'start_seconds':i*.15,'end_seconds':i*.15+.12,'mean_frame_peak_probability':peak} for i,p in enumerate(phones)],'timing_status':'synthetic_test_spans'}
        out[key]={'prompt_id':prompt,'response':interpret_live(pred,PROMPTS[prompt],{},'word')}
    folder=ROOT/'data/results/american_expansion';folder.mkdir(parents=True,exist_ok=True)
    (folder/'ui_fixtures.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Wrote {len(out)} synthetic decoded-label UI fixtures.')
if __name__=='__main__':main()

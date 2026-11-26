"""Render original schematic sound references from the catalog, not measured poses."""
from html import escape
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.sound_catalog import CONSONANT_FEATURES, FILENAMES, GUIDES, VOWEL_FEATURES, MOVING_VOWELS, AIRFLOW, PRIMARY_TARGETS


def make_svg(phone):
    if phone in MOVING_VOWELS:
        start,end=MOVING_VOWELS[phone]
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 330" role="img" aria-label="Two reference moments for /{escape(phone)}/, not a measured path">
<rect width="800" height="330" fill="#f6f8f2"/>
<text x="25" y="25" font-family="Segoe UI,Arial,sans-serif" font-size="17" fill="#285d47">Start /{escape(start)}/</text>
<text x="425" y="25" font-family="Segoe UI,Arial,sans-serif" font-size="17" fill="#285d47">Finish /{escape(end)}/</text>
<svg x="0" y="35" width="380" height="280" viewBox="0 0 380 280">{make_svg(start)}</svg>
<svg x="420" y="35" width="380" height="280" viewBox="0 0 380 280">{make_svg(end)}</svg>
<path d="M378 166H414m-9 -6l9 6l-9 6" fill="none" stroke="#a67335" stroke-width="3"/>
</svg>'''
    vowel = phone in VOWEL_FEATURES
    if vowel:
        front, openness, rounded, _ = VOWEL_FEATURES[phone]
        px, py = 125 + 140 * front, 93 + 92 * openness
        tongue = (f'M88 197 Q{px-55:.0f} {py+23:.0f} {px:.0f} {py:.0f} '
                  f'Q{min(284,px+25):.0f} {py+18:.0f} 287 183 Q240 221 169 218 Q114 218 88 197Z')
        if phone in {'ɝ','ɚ'}:
            tongue='M88 197Q120 174 165 119Q205 98 238 123Q251 142 263 156Q270 172 287 183Q205 225 88 197Z'
        top_label = GUIDES[phone]["name"]
        action = 'American r: bunched or curled, without roof contact' if phone in {'ɝ','ɚ'} else "Rounded lips" if rounded else "Unrounded lips"
        mark = (f'<ellipse cx="335" cy="130" rx="12" ry="19" fill="none" stroke="#758e6e" stroke-width="3"/>'
                if rounded else '<path d="M322 123 Q336 130 350 123 M322 139 Q336 132 350 139" fill="none" stroke="#758e6e" stroke-width="3"/>')
        closure = ""
        voice = "Vowel quality reference; duration not measured"
    else:
        place, manner, voiced, _ = CONSONANT_FEATURES[phone]
        top_label = f"{place.capitalize()} {manner}"
        if place == "velar":
            tongue = "M88 197 Q97 114 128 79 Q144 76 155 137 Q206 173 287 183 Q240 221 169 218Q114 218 88 197Z"
        elif place == "alveolar" and manner in {"stop","nasal","lateral","tap"}:
            tongue = "M88 197 Q173 181 249 127 Q272 100 282 88Q289 87 290 120L292 181Q240 221 169 218Q114 218 88 197Z"
        elif place == "postalveolar":
            tongue = "M88 197 Q157 177 210 138Q232 100 249 110Q262 120 287 183Q240 221 169 218Q114 218 88 197Z"
        elif place == "alveolar":
            tongue = "M88 197 Q163 177 245 135Q267 116 281 112Q289 111 291 139L292 183Q240 221 169 218Q114 218 88 197Z"
        elif place == "dental":
            tongue = "M88 197 Q177 173 272 142Q299 116 311 119L313 133Q304 143 292 183Q240 221 169 218Q114 218 88 197Z"
        else:
            tongue = "M88 197 Q180 168 287 183Q240 221 169 218Q114 218 88 197Z"
        if phone=='ɹ':tongue='M88 197Q133 172 196 124Q230 107 258 133Q263 150 275 165L287 183Q205 225 88 197Z'
        if place=='palatal':tongue='M88 197Q140 106 201 89Q246 89 275 150L287 183Q205 225 88 197Z'
        action = AIRFLOW[manner].capitalize()
        if place == "bilabial":
            closure = '<path d="M309 109Q337 111 320 132Q337 153 309 155" fill="none" stroke="#9b6b66" stroke-width="4"/>'
        elif place == "labiodental":
            closure = '<path d="M309 156Q327 137 304 114" fill="none" stroke="#9b6b66" stroke-width="4"/>'
        else:
            closure = ""
        mark = ('<path d="M55 249q6 -12 12 0t12 0t12 0t12 0" fill="none" stroke="#36886b" stroke-width="3"/>'
                if voiced else '<path d="M55 249h48" stroke="#91a18b" stroke-width="2"/>')
        voice = "Voice on" if voiced else "Voice off"
    nasal=not vowel and CONSONANT_FEATURES[phone][1]=='nasal'
    lateral=not vowel and CONSONANT_FEATURES[phone][1]=='lateral'
    arrow = '' if (not vowel and CONSONANT_FEATURES[phone][1] in {"stop","nasal","lateral"}) else '<path d="M238 124Q281 120 315 129" fill="none" stroke="#4591ab" stroke-width="2.5" marker-end="url(#arrow)"/>'
    if nasal:arrow='<path d="M95 152Q84 43 255 48L325 66" fill="none" stroke="#4591ab" stroke-width="3" marker-end="url(#arrow)"/><text x="143" y="43" font-size="12" fill="#347789">Air through nose</text>'
    if lateral:arrow='<path d="M170 162Q230 143 311 148" fill="none" stroke="#4591ab" stroke-width="2.5" stroke-dasharray="5 4" marker-end="url(#arrow)"/><text x="147" y="163" font-size="11" fill="#347789">Air at tongue sides</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 280" role="img" aria-labelledby="title desc">
<title id="title">Reference for /{escape(phone)}/</title><desc id="desc">Original simplified reference for {escape(GUIDES[phone]['name'])}. Not to scale and not the speaker's measured anatomy.</desc>
<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0L6 3L0 6" fill="#4591ab"/></marker></defs>
<rect width="380" height="280" fill="#f6f8f2"/>
<text x="27" y="22" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="#64785c">{escape(top_label)}</text>
<path d="M68 187C55 135 75 82 126 65Q210 34 291 76L310 90L309 110M309 153L310 174Q280 226 204 234Q117 240 68 187" fill="#fffdf7" stroke="#b4bfae" stroke-width="3"/>
<path d="M98 100Q183 53 278 89" fill="none" stroke="#8a9c84" stroke-width="4"/>
<path d="M274 87q8 -4 16 5" fill="none" stroke="#617957" stroke-width="4"/>
<rect x="295" y="90" width="12" height="25" rx="3" fill="white" stroke="#91a18b" stroke-width="2"/>
<rect x="297" y="153" width="11" height="19" rx="3" fill="white" stroke="#91a18b" stroke-width="2"/>
<path d="{tongue}" fill="#d99f98" stroke="#b77771" stroke-width="2"/>{closure}{arrow}{mark}
<text x="123" y="202" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="#743f3a">Tongue</text>
<text x="{'27' if vowel else '120'}" y="253" font-family="Segoe UI,Arial,sans-serif" font-size="{'11' if vowel else '13'}" fill="#56734f">{escape(voice)}</text>
<text x="27" y="273" font-family="Segoe UI,Arial,sans-serif" font-size="11" fill="#64785c">{escape(action)}; schematic reference only</text>
</svg>'''


def main():
    folder = ROOT / "ai-service/app/demo_static"
    for phone in GUIDES:
        (folder / f"{FILENAMES[phone]}.svg").write_text(make_svg(phone), encoding="utf-8")
    print(f"Rendered {len(GUIDES)} references, including {len(PRIMARY_TARGETS)} American primary targets.")


if __name__ == "__main__":
    main()

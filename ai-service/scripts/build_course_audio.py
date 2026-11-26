"""Build the original curriculum prompts with two local US voices and British eSpeak NG."""
import argparse
import ctypes
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import wave
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"ai-service"))
sys.path.append(str(ROOT/"data/speech-tools"))
from app.course.catalog import AUDIO
import av
import numpy as np


def sapi_markup(line):
    pieces=re.split(r"(\*[^*]+\*|\^[^^]+\^|![^!]+!|~)",line)
    tags=[]
    for piece in pieces:
        if piece=="~": tags.append('<silence msec="320"/>')
        elif piece.startswith("*") and piece.endswith("*"):
            tags.append('<emph><pitch middle="+3"><rate speed="-2">'+escape(piece[1:-1])+'</rate></pitch></emph>')
        else: tags.append(escape(piece.strip("^!")))
    return "<rate speed='-1'>"+''.join(tags)+"</rate>"


def british_synth(directory, pending):
    import espeakng_loader as loader
    lib=loader.load_library()
    rate=lib.espeak_Initialize(2,0,str(Path(loader.get_data_path()).parent).encode(),0)
    if rate<=0 or lib.espeak_SetVoiceByName(b"English (Great Britain)")!=0:raise RuntimeError("British reference voice unavailable")
    chunks=[]
    callback_type=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.POINTER(ctypes.c_short),ctypes.c_int,ctypes.c_void_p)
    @callback_type
    def callback(pointer,size,events):
        if pointer and size: chunks.append(ctypes.string_at(pointer,size*2))
        return 0
    lib.espeak_SetSynthCallback(callback)
    for key,(line,accent,_) in AUDIO.items():
        if accent!="en-GB" or key not in pending:continue
        chunks.clear()
        raw=line.encode("utf-8")+b"\0"
        result=lib.espeak_Synth(raw,len(raw),0,1,0,1,None,None)
        if result!=0 or not chunks:raise RuntimeError("Failed British synthesis: "+line)
        with wave.open(str(directory/(key+".wav")),"wb") as wav:
            wav.setparams((1,2,rate,0,"NONE",""))
            wav.writeframes(b"".join(chunks))


def encode(wav,dest,line):
    with wave.open(str(wav),"rb") as src:
        rate=src.getframerate()
        data=np.frombuffer(src.readframes(src.getnframes()),dtype="<i2")
    if not len(data) or np.max(np.abs(data.astype(float)))<200:raise ValueError(f"Silent prompt {line}")
    # Construct the contrasting terminal contours on the voiced end of the model.
    marker=re.search(r"(\^|!)([^!^]+)\1[.?…]*$",line.strip())
    if marker:
        active=np.flatnonzero(np.abs(data.astype(float))>220)
        end=int(active[-1]);start=max(int(active[0]),end-int(.32*rate))
        change=4 if marker[1]=="^" else -4
        positions=np.cumsum(2**(np.linspace(-change/2,change/2,int((end-start)*1.5))/12))
        positions=positions[positions<end-start]
        segment=np.interp(positions,np.arange(end-start),data[start:end]).astype("<i2")
        data=np.concatenate((data[:start],segment,data[end:]))
    with av.open(str(dest),"w",format="mp3") as output:
        stream=output.add_stream("libmp3lame",rate=24000)
        stream.layout="mono";stream.bit_rate=48000
        frame=av.AudioFrame.from_ndarray(data.reshape(1,-1),format="s16",layout="mono")
        frame.sample_rate=rate
        for packet in stream.encode(frame):output.mux(packet)
        for packet in stream.encode():output.mux(packet)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--espeak-dir",type=Path)
    parser.add_argument("--force",action="store_true")
    args=parser.parse_args()
    if args.espeak_dir:sys.path.insert(0,str(args.espeak_dir.resolve()))
    dest=ROOT/"ai-service/app/course/audio";dest.mkdir(exist_ok=True)
    pending={key for key in AUDIO if args.force or not (dest/(key+".mp3")).exists()}
    if not pending:return
    with TemporaryDirectory() as tmp:
        folder=Path(tmp)
        prompts=[dict(key=k,xml=sapi_markup(t),speaker=s) for k,(t,a,s) in AUDIO.items() if a=="en-US" and k in pending]
        (folder/"list.json").write_text(json.dumps(prompts,ensure_ascii=True),encoding="utf-8")
        script="""param([string]$Folder)
$ErrorActionPreference='Stop'
$s=New-Object -ComObject SAPI.SpVoice
$voices=@($s.GetVoices() | Where-Object {$_.GetAttribute('Language') -eq '409'})
if($voices.Count -lt 2){throw 'Two US English SAPI voices required'}
foreach($row in (Get-Content -Raw -LiteralPath (Join-Path $Folder 'list.json') | ConvertFrom-Json)){
 $s.Voice=$voices[$row.speaker]
 $f=New-Object -ComObject SAPI.SpFileStream
 $f.Open((Join-Path $Folder ($row.key+'.wav')),3,$false)
 $s.AudioOutputStream=$f
 [void]$s.Speak($row.xml,136)
 $f.Close()
}
"""
        runner=folder/"build.ps1";runner.write_text(script,encoding="utf-8")
        subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",str(runner),str(folder)],check=True)
        if any(AUDIO[k][1]=="en-GB" for k in pending):british_synth(folder,pending)
        for key in pending:encode(folder/(key+".wav"),dest/(key+".mp3"),AUDIO[key][0])
    print(f"Built {len(AUDIO)} course recordings.")


if __name__=="__main__":main()


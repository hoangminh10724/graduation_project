"""Evaluate a train/validation/test GOP baseline against existing human ratings.

Uses authors' published GOPT/Kaldi LibriSpeech acoustic features, NOT WordSpeak's
currently stubbed raw-audio endpoint. No learned checkpoint or test labels enter
fitting. The official training set is divided using our prepared speaker split.
"""
from collections import defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
FEATURES=ROOT/'data/baselines/gopt'
OUT=ROOT/'data/results/pronunciation_baseline'
MODEL=ROOT/'data/models/gop_linear_baseline'


def read_manifest(name):
    return [json.loads(s) for s in (ROOT/'data/prepared'/f'{name}.jsonl').read_text(encoding='utf-8').splitlines()]


def rankdata(values):
    order=np.argsort(values,kind='stable');sorted_values=values[order]
    starts=np.r_[0,np.flatnonzero(np.diff(sorted_values))+1];ends=np.r_[starts[1:],len(values)]
    ranks=np.empty(len(values),dtype=float)
    for a,b in zip(starts,ends):ranks[order[a:b]]=(a+b-1)/2+1
    return ranks


def corr(a,b):
    if np.ptp(a)<1e-12 or np.ptp(b)<1e-12:return None
    a=a-a.mean();b=b-b.mean();den=np.sqrt(np.dot(a,a)*np.dot(b,b))
    return float(np.dot(a,b)/den) if den>1e-12 else None


def metrics(y,p):
    return dict(n=len(y),mae=float(np.mean(np.abs(y-p))),rmse=float(np.sqrt(np.mean((y-p)**2))),
        pearson=corr(y,p),spearman=corr(rankdata(y),rankdata(p)))


def load_data():
    manifests={name:read_manifest(name) for name in ['train','validation','test']}
    examples={r['id'].split(':',1)[1]:r for rows in manifests.values() for r in rows}
    splits={r['id'].split(':',1)[1]:split for split,rows in manifests.items() for r in rows}
    all_x=[];targets=[];metadata=[];phone_map={};source_hashes={}
    for prefix,official_split in [('tr','train'),('te','test')]:
        x=np.loadtxt(FEATURES/f'{prefix}_feats.csv',delimiter=',',dtype=np.float64)
        keys=np.loadtxt(FEATURES/f'{prefix}_keys_phn.csv',delimiter=',',dtype=str)
        published_labels=np.loadtxt(FEATURES/f'{prefix}_labels_phn.csv',delimiter=',',dtype=str)
        assert x.shape[0]==len(keys)==len(published_labels)
        phone_count=(x.shape[1]-1)//2
        assert x.shape[1]==1+2*phone_count
        assert np.isfinite(x).all()
        ids=x[:,0].astype(int);assert np.array_equal(ids,x[:,0])
        assert np.allclose(x[:,1+phone_count:],x[np.arange(len(x)),1+ids,None]-x[:,1:1+phone_count],atol=2e-5)
        flattened={}
        for key,ex in examples.items():
            if ex['official_split']!=official_split:continue
            flattened[key]=[(wi,pi,ph,float(score)) for wi,w in enumerate(ex['pronunciation_labels']['words'])
                for pi,(ph,score) in enumerate(zip(w['phones'],w['phones-accuracy']))]
        observed=set()
        for i,key in enumerate(keys):
            uid,index=key.rsplit('.',1);index=int(index)
            assert (uid,index) not in observed;observed.add((uid,index))
            wi,pi,symbol,y=flattened[uid][index]
            symbol=re.sub(r'[012]$','',symbol)
            num=int(ids[i])
            assert phone_map.setdefault(num,symbol)==symbol
            assert float(published_labels[i,0])==num
            # Check published labels, but read targets from the original corpus.
            assert abs(float(published_labels[i,1])-y)<1e-5
            targets.append(y)
            metadata.append(dict(id=uid,phone_index=index,word_index=wi,phone=symbol,
                speaker_id=examples[uid]['speaker_id'],split=splits[uid]))
        assert len(observed)==sum(len(v) for v in flattened.values())
        all_x.append(x)
        for suffix in ['feats','keys_phn','labels_phn']:
            path=FEATURES/f'{prefix}_{suffix}.csv'
            with path.open('rb') as f:source_hashes[path.name]=hashlib.file_digest(f,'sha256').hexdigest()
    x=np.concatenate(all_x);y=np.array(targets);phone_count=(x.shape[1]-1)//2
    pid=x[:,0].astype(int)
    # Kaldi defines these differences as canonical LPP - alternative LPP.
    gop=x[:,1+phone_count:].min(axis=1)
    assert gop.max()<1e-5
    features=np.column_stack([x[:,1:],gop,np.eye(phone_count)[pid]])
    masks={name:np.array([r['split']==name for r in metadata]) for name in manifests}
    return features,gop,pid,y,metadata,masks,phone_map,source_hashes,examples


def linear_fit(x,y,ridge):
    mu=x.mean(0);sd=x.std(0);sd[sd<1e-4]=1
    z=(x-mu)/sd
    penalty=np.eye(z.shape[1])*ridge
    weights=np.linalg.solve(z.T@z+penalty,z.T@(y-y.mean()))
    return dict(mean=mu,std=sd,weights=weights,intercept=float(y.mean()),ridge=ridge)


def linear_predict(model,x):
    return np.clip((x-model['mean'])/model['std']@model['weights']+model['intercept'],0,2)


def speaker_ci(y,p,speakers,seed=20261113,repeats=1000):
    unique,idx=np.unique(speakers,return_inverse=True)
    stats=np.column_stack([np.bincount(idx),np.bincount(idx,weights=y),np.bincount(idx,weights=p),
        np.bincount(idx,weights=y*y),np.bincount(idx,weights=p*p),np.bincount(idx,weights=y*p)])
    rng=np.random.default_rng(seed);values=[]
    for _ in range(repeats):
        n,sy,sp,syy,spp,syp=stats[rng.integers(0,len(unique),len(unique))].sum(0)
        den=np.sqrt(max(0,syy-sy*sy/n)*max(0,spp-sp*sp/n))
        if den>0:values.append((syp-sy*sp/n)/den)
    return dict(level=.95,unit='speaker',speakers=len(unique),replicates=repeats,
        pearson_interval=np.quantile(values,[.025,.975]).tolist())


def error_metrics(y,p,threshold):
    true=y<1;pred=p<threshold
    tp=int(np.sum(true&pred));fp=int(np.sum(~true&pred));fn=int(np.sum(true&~pred));tn=int(np.sum(~true&~pred))
    scores=-p;ranks=rankdata(scores);pos=int(true.sum());neg=len(true)-pos
    auc=float((ranks[true].sum()-pos*(pos+1)/2)/(pos*neg)) if pos and neg else None
    return dict(definition='expert phone score below 1 on original 0-2 scale',
        threshold_selected_on_validation=threshold,prevalence=float(true.mean()),roc_auc=auc,
        precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
        false_positive_rate=fp/(fp+tn) if fp+tn else None,tp=tp,fp=fp,fn=fn,tn=tn)


def main():
    OUT.mkdir(parents=True,exist_ok=True);MODEL.mkdir(parents=True,exist_ok=True)
    print('Loading and checking acoustic features against original annotations',flush=True)
    x,gop,pid,y,meta,masks,phone_map,hashes,examples=load_data()
    tr,va,te=(masks[k] for k in ['train','validation','test'])
    means=np.array([y[tr&(pid==i)].mean() if np.any(tr&(pid==i)) else y[tr].mean() for i in range(pid.max()+1)])
    predictions={'training_mean':np.full(len(y),y[tr].mean()),'phone_identity_prior':means[pid]}
    candidates={};selection=[]
    # A near-unregularized two-parameter scalar GOP calibration.
    candidates['scalar_gop']=linear_fit(gop[tr,None],y[tr],1e-6)
    predictions['scalar_gop']=linear_predict(candidates['scalar_gop'],gop[:,None])
    selection.append(dict(model='scalar_gop',**metrics(y[va],predictions['scalar_gop'][va])))
    for alpha in [.01,.1,1,10,100,1000,10000]:
        name=f'acoustic_ridge_{alpha:g}'
        model=linear_fit(x[tr],y[tr],alpha)
        p=linear_predict(model,x)
        candidates[name]=model;predictions[name]=p
        selection.append(dict(model=name,**metrics(y[va],p[va])))
    best=min(selection,key=lambda r:r['rmse'])['model']
    model=candidates[best];p=predictions[best]
    print('Validation-selected model:',best,flush=True)
    # Threshold fixed from validation negatives, before accessing test metrics.
    threshold=float(np.quantile(p[va&(y>=1)],.10))
    test_metrics={name:metrics(y[te],pred[te]) for name,pred in predictions.items()
                  if name in ['training_mean','phone_identity_prior','scalar_gop',best]}
    speakers=np.array([r['speaker_id'] for r in meta])
    ci=speaker_ci(y[te],p[te],speakers[te])
    errors=error_metrics(y[te],p[te],threshold)
    operating_points=[]
    for rate in [.01,.05,.10]:
        point_threshold=float(np.quantile(p[va&(y>=1)],rate))
        operating_points.append(dict(validation_target_false_positive_rate=rate,
            **error_metrics(y[te],p[te],point_threshold)))
    # An explicitly heuristic sentence score; no fluency/prosody claims.
    test_utterances=defaultdict(list)
    for i in np.flatnonzero(te):test_utterances[meta[i]['id']].append(i)
    sentence_rows=[]
    for uid,indices in test_utterances.items():
        sentence_rows.append(dict(id=uid,speaker_id=examples[uid]['speaker_id'],
            human_accuracy=float(examples[uid]['pronunciation_labels']['accuracy']),
            predicted_mean_phone_times_5=float(p[indices].mean()*5)))
    sentence=metrics(np.array([r['human_accuracy'] for r in sentence_rows]),
        np.array([r['predicted_mean_phone_times_5'] for r in sentence_rows]))
    report=dict(experiment='Linear GOP-feature baseline versus expert pronunciation scores',
        selected_model=best,selection_metric='minimum validation phone RMSE',
        splits={name:dict(utterances=len(set(meta[i]['id'] for i in np.flatnonzero(mask))),
            speakers=len(set(speakers[mask])),phonemes=int(mask.sum())) for name,mask in masks.items()},
        validation_candidates=selection,test_phone_metrics=test_metrics,
        selected_model_speaker_bootstrap=ci,severe_error_detection=errors,
        error_detection_operating_points=operating_points,
        heuristic_sentence_accuracy=sentence,
        source_features='Published GOPT LibriSpeech/Kaldi GOP acoustic features, not freshly extracted by WordSpeak',
        feature_source='https://github.com/YuanGongND/gopt/tree/master/data',
        feature_sha256=hashes,phone_id_mapping=phone_map,
        labels='Original resource/scores.json ratings, cross-checked against the published feature labels',
        limitations=['The production /assess endpoint is still a fixed-score stub and was not evaluated here.',
            'This experiment uses the public Mandarin-L1 speechocean762 corpus, including child speech.',
            'No accuracy claim is established for Vietnamese learners or the native comparison collection.',
            'Kaldi reference features are not a validation of the planned wav2vec2 frontend.',
            'Sentence results are mean predicted phone scores times five, not an independently trained sentence model.',
            'Reference features use known corpus text/alignment; production recognition/alignment failures are not represented.'])
    (OUT/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    config=dict(model=best,input='canonical phone ID + 42 LPP + 42 LPR from documented Kaldi recipe',
        features='84 acoustic values, minimum LPR (GOP), and 42-way canonical phone indicator',
        phone_id_mapping=phone_map,output_scale=[0,2],test_not_used_for_selection=True,
        feature_source=report['feature_source'],limitations=report['limitations'])
    (MODEL/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    np.savez(MODEL/'weights.npz',**model)
    with np.load(MODEL/'weights.npz',allow_pickle=False) as saved:
        restored={k:saved[k] for k in saved.files}
    reloaded=linear_predict(restored,gop[:,None] if best=='scalar_gop' else x)
    assert np.allclose(reloaded,p,atol=1e-12)
    with (OUT/'phone_predictions.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['utterance_id','speaker_id','phone_index','phone','human_score','predicted_score','scalar_gop_score','phone_prior_score']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for i in np.flatnonzero(te):
            writer.writerow(dict(utterance_id=meta[i]['id'],speaker_id=meta[i]['speaker_id'],
                phone_index=meta[i]['phone_index'],phone=meta[i]['phone'],human_score=float(y[i]),
                predicted_score=float(p[i]),scalar_gop_score=float(predictions['scalar_gop'][i]),phone_prior_score=float(means[pid[i]])))
    with (OUT/'sentence_predictions.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(sentence_rows[0]));writer.writeheader();writer.writerows(sentence_rows)
    assert not (set(speakers[te]) & (set(speakers[tr])|set(speakers[va])))
    print(json.dumps({k:report[k] for k in ['selected_model','splits','test_phone_metrics','selected_model_speaker_bootstrap','severe_error_detection','heuristic_sentence_accuracy']},indent=2),flush=True)
    # Plot is optional for reruns; numerical results are always saved.
    try:
        os.environ.setdefault('MPLCONFIGDIR',str(OUT/'plot_cache'))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
        density=axes[0].hexbin(y[te],p[te],gridsize=25,mincnt=1,bins='log',cmap='Blues')
        fig.colorbar(density,ax=axes[0],label='Phones per bin (log scale)',fraction=.045,pad=.03)
        axes[0].plot([0,2],[0,2],'--',color='#d35b36',linewidth=1)
        axes[0].set(xlabel='Expert phone score (0–2)',ylabel='Predicted phone score (0–2)',
            title=f'Unseen speakers: Pearson r = {test_metrics[best]["pearson"]:.3f}',xlim=(-.05,2.05),ylim=(-.05,2.05))
        names=list(test_metrics);vals=[test_metrics[n]['mae'] for n in names]
        display={'training_mean':'Training mean','phone_identity_prior':'Phone identity only','scalar_gop':'Scalar GOP',best:'Selected model'}
        axes[1].barh([display[n] for n in names],vals,color=['#a8afb9','#8798b0','#5588aa','#226c60'][:len(names)])
        axes[1].invert_yaxis();axes[1].set(xlabel='Mean absolute error (0–2 scale)',title='Controls versus acoustic baseline')
        fig.suptitle('GOP baseline versus existing human ratings — speechocean762')
        fig.savefig(OUT/'human_agreement.png',dpi=160);plt.close(fig)
    except ImportError:
        print('Matplotlib unavailable: numerical outputs saved; plot skipped',flush=True)
    lines=['# Pronunciation baseline versus human ratings','','This is a measured experiment, not a file-format audit. It uses the GOPT authors\' published acoustic features from a pretrained LibriSpeech/Kaldi recognizer and original speechocean762 expert labels. It does not call the stubbed WordSpeak API.','','## Design','',
        '- Training: 2,000 utterances / 100 speakers. Validation: 500 / 25. Test: 2,500 / 125.',
        '- No speaker overlap. Fitting/scaling uses training only. Hyperparameters use validation RMSE only.',
        '- All 94,445 feature rows matched canonical phone positions and original human ratings.',
        '- Original 0–2 scores are used and match the published feature archive labels.',
        '- Controls: a training-mean score and a phone-identity prior with no acoustic information.',
        '- Native and Vietnamese comparison recordings are not used for fitting or reported as human-rated.','',
        '## Held-out phone results','','| Model | MAE (0–2) | RMSE | Pearson r | Spearman rho |','|---|---:|---:|---:|---:|']
    for name,m in test_metrics.items():
        lines.append(f'| {name} | {m["mae"]:.4f} | {m["rmse"]:.4f} | {m["pearson"] if m["pearson"] is not None else "undefined (constant)"} | {m["spearman"] if m["spearman"] is not None else "undefined (constant)"} |')
    lo,hi=ci['pearson_interval']
    lines += ['',f'Selected on validation data: **{best}**. Speaker-bootstrap 95% interval for test Pearson r: **{lo:.3f}–{hi:.3f}** (1,000 resamples of 125 speakers).','',
        '## Detecting low expert-rated phones','',
        f'Low-rating criterion: expert phone score < 1. Test prevalence: {errors["prevalence"]:.1%}. ROC AUC: {errors["roc_auc"]:.3f}.',
        f'At a threshold fixed from validation negatives: precision {errors["precision"]:.1%}, recall {errors["recall"]:.1%}, test false-positive rate {errors["false_positive_rate"]:.1%}.',
        'The low prevalence matters: a respectable correlation or AUC does not guarantee that individual error warnings are reliable.','',
        '| Validation false-alarm target | Test precision | Test recall | Test false-positive rate |',
        '|---|---:|---:|---:|']
    for point in operating_points:
        lines.append(f'| {point["validation_target_false_positive_rate"]:.0%} | {point["precision"]:.1%} | {point["recall"]:.1%} | {point["false_positive_rate"]:.1%} |')
    lines += ['',
        '## Sentence aggregation','',
        f'Mean predicted phone score × 5 versus expert sentence accuracy: Pearson r {sentence["pearson"]:.3f}, MAE {sentence["mae"]:.3f} on the 0–10 scale.',
        'This is a heuristic aggregation, not fluency/prosody scoring and not a separately trained sentence model.','',
        '## Limits and next step','']+['- '+s for s in report['limitations']]+['',
        'This experiment establishes only how this lightweight reference-feature baseline agrees with the existing experts on this corpus. It does not establish Vietnamese performance or production readiness. The next implementation step is the raw-audio phoneme/alignment/GOP frontend and an independent human-rated Vietnamese evaluation subset.','',
        '## Sources','',
        '- Features and code: https://github.com/YuanGongND/gopt/tree/master/data (Yuan Gong et al., ICASSP 2022).',
        '- Kaldi feature definition: https://github.com/kaldi-asr/kaldi/blob/master/src/bin/compute-gop.cc .',
        '- Expert labels: Junbo Zhang et al., speechocean762, Interspeech 2021, https://openslr.org/101/ (CC BY 4.0).',
        '- `metrics.json` contains feature hashes and exact configuration. `phone_predictions.csv` / `sentence_predictions.csv` contain the actual held-out predictions.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('COMPLETE',OUT,flush=True)


if __name__=='__main__':main()

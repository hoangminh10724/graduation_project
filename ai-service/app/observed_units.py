"""Build observed units from decoded labels without consulting the target word."""
from .english_inventory import normalize_label, PAIR_LABELS, R_SEQUENCES

def observed_units(prediction):
    units=[]
    for phone,span in zip(prediction['predicted_phones'],prediction['spans']):
        units.append({**span,'phone':normalize_label(phone),'raw_labels':[phone],'combined':False})
    result=[];index=0
    while index<len(units):
        first=units[index]
        if index+1<len(units):
            second=units[index+1];pair=(first['phone'],second['phone'])
            combined=PAIR_LABELS.get(pair) or next((p for p,parts in R_SEQUENCES.items() if parts==pair),None)
            close=second['start_seconds']-first['end_seconds']<=.12
            short=second['end_seconds']-first['start_seconds']<=1.5
            if combined and close and short:
                result.append({**first,'phone':combined,'end_seconds':second['end_seconds'],
                               'mean_frame_peak_probability':min(first['mean_frame_peak_probability'],second['mean_frame_peak_probability']),
                               'raw_labels':first['raw_labels']+second['raw_labels'],'combined':True})
                index+=2;continue
        result.append(first);index+=1
    return result

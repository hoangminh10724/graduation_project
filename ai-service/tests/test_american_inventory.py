"""American contrasts, focal positions and evidence limitations."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.sound_catalog import PRIMARY_TARGETS, PROMPTS, GUIDES
from app.pronunciation_demo import interpret_live
from app.observed_units import observed_units
from app.teaching_guides import teaching_config

WORDS={
 'seat':['s','i','t'],'sit':['s','ɪ','t'],'bed':['b','ɛ','d'],'bad':['b','æ','d'],
 'food':['f','u','d'],'foot':['f','ʊ','t'],'about':['ə','b','aʊ','t'],'cup':['k','ʌ','p'],
 'hot':['h','ɑ','t'],'caught':['k','ɔ','t'],'bird':['b','ɝ','d'],'teacher':['t','i','tʃ','ɚ'],
 'day':['d','eɪ'],'my':['m','aɪ'],'boy':['b','ɔɪ'],'go':['ɡ','oʊ'],'now':['n','aʊ'],
 'pen':['p','ɛ','n'],'ben':['b','ɛ','n'],'ten':['t','ɛ','n'],'den':['d','ɛ','n'],
 'key':['k','i'],'give':['ɡ','ɪ','v'],'fan':['f','æ','n'],'van':['v','æ','n'],
 'thin':['θ','ɪ','n'],'this':['ð','ɪ','s'],'see':['s','i'],'zoo':['z','u'],'she':['ʃ','i'],
 'vision':['v','ɪ','ʒ','ə','n'],'hat':['h','æ','t'],'chin':['tʃ','ɪ','n'],'jam':['dʒ','æ','m'],
 'man':['m','æ','n'],'no':['n','oʊ'],'sing':['s','ɪ','ŋ'],'lip':['l','ɪ','p'],
 'red':['ɹ','ɛ','d'],'wet':['w','ɛ','t'],'yes':['j','ɛ','s'],
}

def prediction(phones, peak=.9):
    return {'predicted_phones':phones,'spans':[{'phone':phone,'start_seconds':i*.15,'end_seconds':i*.15+.12,'mean_frame_peak_probability':peak} for i,phone in enumerate(phones)],'timing_status':'synthetic_spans'}

def compare(phones,prompt,peak=.9):return interpret_live(prediction(phones,peak),PROMPTS[prompt],{},'word')

@pytest.mark.parametrize('word',list(WORDS))
def test_all_core_targets_have_a_functional_reference_comparison(word):
    result=compare(WORDS[word],word)
    assert result['predicted_phone']==PROMPTS[word]['target_phone']
    assert result['status']=='model_match' and result['score'] is None
    assert result['diagnosis']['anatomy_measured'] is False

def test_inventory_is_american_and_has_no_rp_only_core_targets():
    response=TestClient(app).get('/demo/config').json()
    assert response['accent']['id']=='general_american'
    assert response['inventory_counts']=={'core':41,'vowels':17,'consonants':24}
    assert not {'ɒ','ɜː','əʊ','ɪə','eə','ʊə'} & set(PRIMARY_TARGETS)
    assert set(WORDS)=={p['id'] for p in response['prompts'] if p['primary']}
    assert all(p['recognition_status']=='experimental_unvalidated' for p in response['prompts'])

def test_final_nasal_and_medial_fricative_use_their_word_positions():
    final=compare(['s','ɪ','n'],'sing')
    assert final['predicted_phone']=='n'
    assert 'back' in final['diagnosis']['adjustment']
    middle=compare(['v','ɪ','s','ə','n'],'vision')
    assert middle['predicted_phone']=='s' and middle['status']=='possible_difference'
    assert middle['predicted_phone']!='v'

def test_missing_final_consonant_is_not_invented():
    result=compare(['s','ɪ'],'sing')
    assert result['predicted_phone'] is None and 'No final consonant' in result['message']

def test_extra_g_after_ng_does_not_replace_the_actual_nasal_candidate():
    result=compare(['s','ɪ','ŋ','ɡ'],'sing')
    assert result['predicted_phone']=='ŋ' and result['status']=='uncertain'
    assert result['details']['trailing_model_labels']==['ɡ']
    assert 'extra' in result['diagnosis']['adjustment']

def test_schwa_and_unstressed_r_are_selected_by_nucleus_position():
    assert compare(['ʌ','b','aʊ','t'],'about')['predicted_phone']=='ʌ'
    assert compare(['t','i','tʃ','ə'],'teacher')['predicted_phone']=='ə'

@pytest.mark.parametrize('phones,word,heard',[
    (['t','ʃ','ɪ','n'],'chin','tʃ'),(['d','ʒ','æ','m'],'jam','dʒ'),
    (['d','e','ɪ'],'day','eɪ'),(['b','ɜː','ɹ','d'],'bird','ɝ'),
])
def test_split_labels_are_combined_conditionally_without_changing_raw_output(phones,word,heard):
    result=compare(phones,word)
    assert result['predicted_phone']==heard and result['status']=='uncertain'
    assert result['raw_phones']==phones
    assert result['details']['unresolved_reason']=='combined_model_labels'

def test_a_pause_prevents_combining_two_vowels_into_a_diphthong():
    pred=prediction(['e','ɪ']);pred['spans'][1].update(start_seconds=.7,end_seconds=.8)
    assert len(observed_units(pred))==2
    result=interpret_live(pred,PROMPTS['day'],{},'word')
    assert result['predicted_phone'] is None

@pytest.mark.parametrize('peak',[.2,.9])
def test_cot_caught_merger_is_not_given_a_wrong_sound_correction(peak):
    result=compare(['k','ɑ','t'],'caught',peak)
    assert result['details']['accepted_variant']=='cot_caught_merger'
    assert result['diagnosis']['kind']=='accepted_variant'
    assert result['articulation_feedback']['differences']==[]
    assert 'No change is required' in result['diagnosis']['adjustment']

def test_r_vowel_stress_is_not_inferred_from_one_model_label():
    result=compare(['b','ɚ','d'],'bird')
    assert result['status']=='uncertain'
    assert result['details']['unresolved_reason']=='stress_not_assessed'
    assert 'No stress' in result['diagnosis']['adjustment']

def test_long_vowel_model_notation_does_not_create_an_american_length_error():
    result=compare(['s','iː','t'],'seat')
    assert result['predicted_phone']=='i' and result['raw_phones'][1]=='iː'
    assert result['status']=='model_match' and not result['details']['vowel_duration_assessed']

@pytest.mark.parametrize('phones,word',[(['pʰ','ɛ','n'],'pen'),(['tʰ','ɛ','n'],'ten'),(['kʰ','i'],'key')])
def test_normal_american_aspiration_is_not_a_wrong_consonant(phones,word):
    result=compare(phones,word)
    assert result['status']=='model_match' and result['raw_phones']==phones

def test_one_steady_model_label_does_not_prove_a_missing_american_glide():
    result=compare(['d','e'],'day')
    assert result['status']=='uncertain' and result['predicted_phone']=='e'
    assert result['details']['unresolved_reason']=='glide_resolution_unverified'
    assert result['diagnosis']['adjustment'].startswith('If ')

def test_nasal_to_stop_difference_explains_nasal_airflow():
    result=compare(['b','æ','n'],'man')
    assert result['predicted_phone']=='b'
    assert 'nose' in result['diagnosis']['adjustment']
    assert result['articulation_feedback']['target_reference']['features']['airflow']=='air through nose'

def test_extra_r_combinations_and_all_moving_references_have_complete_poses():
    config=teaching_config()
    for phone in ['eɪ','aɪ','ɔɪ','oʊ','aʊ','ɪɹ','ɛɹ','ɑɹ','ɔɹ','ʊɹ','aɪɹ']:
        assert phone in GUIDES and phone in config['lessons']
        pose=config['poses'][phone]
        assert pose['moving'] and len(pose['path_poses'])>=2
    assert config['poses']['w']['lip_round']>0
    assert config['poses']['m']['lip_closed']

def test_changing_a_diphthong_target_does_not_change_the_observed_sound():
    first=compare(['d','aɪ'],'day');second=compare(['d','aɪ'],'my')
    assert first['predicted_phone']==second['predicted_phone']=='aɪ'

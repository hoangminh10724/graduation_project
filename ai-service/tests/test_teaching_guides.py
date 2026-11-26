from fastapi.testclient import TestClient
from app.main import app
from app.sound_catalog import PRIMARY_TARGETS
from app.teaching_guides import teaching_config


def test_discovery_lessons_cover_primary_targets_and_have_usable_example_poses():
    config = teaching_config()
    assert set(PRIMARY_TARGETS) <= set(config['lessons'])
    for target, lesson in config['lessons'].items():
        assert target in config['poses'] and lesson['anchor_phone'] in config['poses']
        assert len(lesson['steps']) == 4
        assert lesson['steps'][0]['progress'] == 0 and lesson['steps'][-1]['progress'] == 100
        assert set(lesson['controls']) == {'lips','tongue','jaw','voice'}
        assert all(step['focus'] in lesson['controls'] for step in lesson['steps'])
        assert lesson['source']['url'].startswith('https://')
        assert 3 < len(lesson['quick_cue'].split()) <= 25


def test_stops_use_closure_release_examples_and_fricatives_use_continuous_flow():
    lessons = teaching_config()['lessons']
    assert all(lessons[p]['mode'] == 'release' for p in ['p','t','k'])
    assert lessons['s']['mode'] == lessons['ʃ']['mode'] == 'flow'
    assert lessons['s']['anchor_phone'] == 'ʃ'
    assert lessons['ʃ']['anchor_phone'] == 's'


def test_teaching_pose_directions_match_the_named_examples():
    poses = teaching_config()['poses']
    assert poses['ʃ']['front'] < poses['s']['front']
    assert poses['æ']['opening'] > poses['ɛ']['opening']
    assert poses['uː']['rounded'] and not poses['iː']['rounded']
    assert poses['iː']['lip_spread'] > poses['ɪ']['lip_spread'] > poses['ɑ']['lip_spread']
    assert poses['uː']['lip_round'] > poses['iː']['lip_round']
    assert poses['p']['lip_closed'] and not poses['t']['lip_closed']
    from app.sound_catalog import GUIDES
    assert GUIDES['i']['tips'] == GUIDES['iː']['tips']
    assert GUIDES['iː']['tips'][0] != GUIDES['ɪ']['tips'][0]
    assert GUIDES['iː']['tips'][1] != GUIDES['ɪ']['tips'][1]


def test_config_exposes_practice_separately_from_recording_predictions():
    response = TestClient(app).get('/demo/config').json()
    assert response['teaching']['revision'] == 'american-inventory-1'
    assert 'predicted_phone' not in response['teaching']
    assert 'informed by Adrian Underhill' in response['teaching']['credit']

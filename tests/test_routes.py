"""End-to-end tests through the Flask route, using the share-link cases."""
import pytest

import app as A
from generate_test_links import test_cases as SHARE_LINK_CASES


@pytest.fixture
def client():
    A.app.config['TESTING'] = True
    return A.app.test_client()


def test_home_page_loads(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'CargoBee' in r.data
    assert b'Calculation Error' not in r.data


@pytest.mark.parametrize('case', SHARE_LINK_CASES, ids=lambda c: c['name'])
def test_share_link_cases_produce_a_plan(client, case):
    r = client.get('/', query_string=case['params'])
    assert r.status_code == 200
    html = r.data.decode()
    assert 'Calculation Error' not in html
    assert 'Total Cargo Weight' in html


def test_post_matches_get(client):
    params = SHARE_LINK_CASES[0]['params']
    get_html = client.get('/', query_string=params).data
    post_html = client.post('/', data=params).data
    assert get_html == post_html


def test_bad_input_shows_readable_error(client):
    r = client.get('/', query_string={'total_cartons': 'abc'})
    html = r.data.decode()
    assert 'Total cartons must be a number' in html
    assert 'invalid literal' not in html

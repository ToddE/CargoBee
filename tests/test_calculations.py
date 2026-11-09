"""Tests for CargoBee's load calculations.

The invariant tests run every palletized plan in a grid of inputs and check
rules that must hold for any input: every carton ships, nothing is taller than
its container, nothing is over the weight limit, and the totals agree with the
manifest.
"""
import itertools

import pytest

import app as A

LIMIT = A.ROAD_WEIGHT_LIMIT_KG

BASE_INPUT = dict(
    total_cartons='1200', carton_l='40', carton_w='30', carton_h='25',
    carton_weight='15', pallet_l='120', pallet_w='100', pallet_h='15',
    pallet_weight='20', max_pallet_h='160',
)


def palletized(**overrides):
    return A.calculate_palletized_load({**BASE_INPUT, **overrides}, LIMIT)


def cartons_shipped(result):
    return sum(p['count'] * p['cartons'] for c in result['pallet_configs'] for p in c['pallets'])


def pallets_listed(result):
    return sum(p['count'] for c in result['pallet_configs'] for p in c['pallets'])


# --- Invariants over a grid of inputs ---------------------------------------

GRID = list(itertools.product(
    ['1', '37', '1200', '2000', '3333', '5000'],   # total_cartons
    ['10', '15', '30', '40'],                       # pallet_h
    ['20', '25', '33'],                             # carton_h
    ['2', '15', '40'],                              # carton_weight
    ['150', '180', '240'],                          # max_pallet_h
))


@pytest.mark.parametrize('total,pallet_h,carton_h,carton_weight,max_h', GRID)
def test_palletized_invariants(total, pallet_h, carton_h, carton_weight, max_h):
    try:
        r = palletized(total_cartons=total, pallet_h=pallet_h, carton_h=carton_h,
                       carton_weight=carton_weight, max_pallet_h=max_h)
    except ValueError:
        pytest.skip('input rejected as infeasible')

    assert cartons_shipped(r) == int(total), 'cartons shipped must equal cartons ordered'
    assert r['total_pallets'] == pallets_listed(r), 'total_pallets must match the manifest'

    for c in r['pallet_configs']:
        container = c['viz_data']['container']
        items = c['viz_data']['items']
        assert len(items) == sum(p['count'] for p in c['pallets']), \
            '3D view must place every pallet in the manifest'
        assert c['weight'] <= LIMIT
        for p in c['pallets']:
            # Listed pallet height must match what is physically built.
            assert p['height'] == pytest.approx(p['layers'] * float(carton_h) + float(pallet_h))
        for it in items:
            assert it['z'] + it['h'] <= container['height'] + 1e-9, 'stack taller than container'
            if it['z'] == 0:
                assert it['h'] <= A.CONTAINER_DOOR_HEIGHT_LIMIT_CM


# --- Regression tests for specific bugs -------------------------------------

def test_topper_height_uses_actual_pallet_height():
    # Previously the Topper pass assumed a 15 cm pallet, so with a 40 cm pallet
    # it showed a 255 cm stack that was really 280 cm (taller than a High Cube).
    r = palletized(total_cartons='2000', carton_weight='10', pallet_h='40', max_pallet_h='165')
    for c in r['pallet_configs']:
        for p in c['pallets']:
            assert p['height'] == p['layers'] * 25 + 40


@pytest.mark.parametrize('total', ['1200', '3333'])
def test_remnant_rebuilt_after_topper_pass(total):
    # Previously 1200 cartons shipped as 1209 and 3333 as 3324.
    assert cartons_shipped(palletized(total_cartons=total)) == int(total)


def test_total_pallets_counts_toppers():
    # Previously reported 27 pallets when the manifest listed 30.
    r = palletized(total_cartons='1200')
    assert any(p['type'] == 'Topper' for c in r['pallet_configs'] for p in c['pallets'])
    assert r['total_pallets'] == pallets_listed(r)


# --- Input validation ------------------------------------------------------

@pytest.mark.parametrize('field,value,message', [
    ('carton_l', '-40', 'Carton length must be greater than zero'),
    ('total_cartons', 'abc', "Total cartons must be a number"),
    ('total_cartons', '10.5', 'Total cartons must be a whole number'),
    ('pallet_h', '', 'Pallet height is required'),
    ('carton_h', 'inf', 'Carton height must be a finite number'),
])
def test_bad_input_is_rejected(field, value, message):
    with pytest.raises(ValueError, match=message):
        palletized(**{field: value})


def test_zero_pallet_weight_is_allowed():
    assert palletized(pallet_weight='0')['recommendation']


def test_carton_larger_than_pallet():
    with pytest.raises(ValueError, match='larger than the pallet'):
        palletized(carton_l='130', carton_w='110')


def test_pallet_over_door_height_is_capped():
    r = palletized(max_pallet_h='400', carton_h='20')
    for c in r['pallet_configs']:
        for p in c['pallets']:
            assert p['height'] <= A.CONTAINER_DOOR_HEIGHT_LIMIT_CM


# --- Floor-loaded ----------------------------------------------------------

@pytest.mark.parametrize('total', ['1', '1500', '5000', '20000'])
def test_floor_load_ships_every_carton_within_weight(total):
    r = A.calculate_floor_load(dict(total_cartons=total, carton_l='40', carton_w='30',
                                    carton_h='25', carton_weight='12'), LIMIT)
    shipped = sum(int(c['items'][0].split()[2]) for c in r['pallet_configs'])
    assert shipped == int(total)
    assert r['weight_status'] == 'OK'
    assert all(c['weight'] <= LIMIT for c in r['pallet_configs'])


def test_floor_load_rejects_carton_heavier_than_limit():
    with pytest.raises(ValueError, match='heavier than the road weight limit'):
        A.calculate_floor_load(dict(total_cartons='1', carton_l='40', carton_w='30',
                                    carton_h='25', carton_weight='30000'), LIMIT)

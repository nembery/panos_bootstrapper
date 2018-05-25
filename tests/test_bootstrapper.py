import pytest
from flask import json

from bootstrapper import bootstrapper


@pytest.fixture
def client():
    client = bootstrapper.app.test_client()

    yield client


def test_index(client):
    """
    Hello world test!
    :param client: test client
    :return: test assertions
    """
    rv = client.get('/')
    assert b'Bootstrapper' in rv.data


def set_object(client, contents):
    """
    Tests the set_object api for the caching system
    :param client: test client
    :return: test assertions
    """
    params = {
        'contents': contents
    }
    return client.post('/api/v0.1/set_object', data=json.dumps(params), content_type='application/json')


def get_object(client, key):
    """
    Test the caching system get_object
    :param client: test client
    :return: test assertions
    """
    params = {
        'key': key
    }
    return client.post('/api/v0.1/get_object', data=json.dumps(params), content_type='application/json')


def test_caching(client):
    """
    Tests tests the caching system get and set objects
    :param client: test client
    :return: test assertions
    """
    r = set_object(client, 'HI THERE')
    d = json.loads(r.data)
    assert d['success'] is True
    assert d['key'] is not None

    key = d['key']
    r = get_object(client, key)
    d = json.loads(r.data)
    assert d['contents'] == 'HI THERE'


def test_build_openstack_bootstrap(client):
    """
    Tests build_bootstrap with deploy option set to openstack
    :param client: test client
    :return: test assertions
    """
    params = {
        "deployment_type": "openstack",
        "hostname": "panos-81",
        "auth_key": "v123",
        "management_ip": "192.168.1.100",
        "management_mask": "255.255.255.0",
        "management_gateway": "192.168.1.254",
        "management_network": "mgmt",
        "management_subnet": "mgmt-subnet",
        "dns_server": "192.168.1.2",
        "image_name": "panos-81.img",
        "image_flavor": "m1.xlarge",
        "outside_network": "outside",
        "outside_subnet": "outside-subnet",
        "outside_ip": "192.168.2.100",
        "inside_network": "inside",
        "inside_subnet": "inside-subnet",
        "inside_ip": "192.168.3.100",
        "ethernet2_1_profile": "PINGSSHTTPS",
        "ethernet1_1_profile": "PINGSSHTTPS",
        "default_next_hop": "10.10.10.10"
    }
    r = client.post('/api/v0.1/build_bootstrap', data=json.dumps(params), content_type='application/json')
    print r.data
    d = json.loads(r.data)
    assert d['openstack_config'] is not None
    assert d['openstack_config']['hostname'] == "panos-81"
    assert d['success'] is True


def test_build_base_configs(client):
    """
    Tests build base_configs
    :param client: test client
    :return: test assertions
    """
    params = {
        "deployment_type": "openstack",
        "hostname": "panos-81",
        "auth_key": "v123",
        "management_ip": "192.168.1.100",
        "management_mask": "255.255.255.0",
        "management_gateway": "192.168.1.254",
        "dns_server": "192.168.1.2",
        "ethernet2_1_profile": "PINGSSHTTPS",
        "ethernet1_1_profile": "PINGSSHTTPS",
        "default_next_hop": "10.10.10.10"
    }
    r = client.post('/api/v0.1/debug_base_config', data=json.dumps(params), content_type='application/json')
    print r.data
    d = json.loads(r.data)
    assert d['success'] is True


def test_build_openstack_configs(client):
    """
    Tests build openstack_configs
    :param client: test client
    :return: test assertions
    """
    params = {
        "deployment_type": "openstack",
        "hostname": "panos-81",
        "auth_key": "v123",
        "management_ip": "192.168.1.100",
        "management_mask": "255.255.255.0",
        "management_gateway": "192.168.1.254",
        "dns_server": "192.168.1.2",
        "outside_ip": "192.168.2.100",
        "inside_ip": "192.168.3.100",
        "ethernet2_1_profile": "PINGSSHTTPS",
        "ethernet1_1_profile": "PINGSSHTTPS",
        "default_next_hop": "10.10.10.10"
    }
    r = client.post('/api/v0.1/debug_openstack_config', data=json.dumps(params), content_type='application/json')
    print r.data
    d = json.loads(r.data)
    assert d['success'] is True


def test_build_openstack_archive(client):
    """
    Tests build openstack_configs
    :param client: test client
    :return: test assertions
    """
    params = {
        "deployment_type": "openstack",
        "hostname": "panos-81",
        "auth_key": "v123",
        "management_ip": "192.168.1.100",
        "management_mask": "255.255.255.0",
        "management_gateway": "192.168.1.254",
        "dns_server": "192.168.1.2",
        "outside_ip": "192.168.2.100",
        "inside_ip": "192.168.3.100",
        "ethernet2_1_profile": "PINGSSHTTPS",
        "ethernet1_1_profile": "PINGSSHTTPS",
        "default_next_hop": "10.10.10.10"
    }
    r = client.post('/api/v0.1/generate_openstack_archive', data=json.dumps(params), content_type='application/json')
    print r.data
    d = json.loads(r.data)
    assert d['success'] is True

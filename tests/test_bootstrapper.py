import pytest
from flask import json
import time

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
    print("Test: Basic Availability".center(79, '-'))

    rv = client.get('/')
    assert b'Bootstrapper' in rv.data


def test_caching(client):
    """
    Tests tests the caching system get and set objects
    :param client: test client
    :return: test assertions
    """
    print("Test: Caching".center(79, '-'))

    params = {
        'contents': 'HI THERE'
    }
    r = client.post('/set', data=json.dumps(params), content_type='application/json')
    d = json.loads(r.data)
    assert d['success'] is True
    assert d['key'] is not None

    key = d['key']
    r = client.get('/get/%s' % key)
    d = r.data
    assert b'HI THERE' in d


# def test_build_openstack_bootstrap(client):
#     """
#     Tests build_bootstrap with deploy option set to openstack
#     :param client: test client
#     :return: test assertions
#     """
#     params = {
#         "deployment_type": "openstack",
#         "bootstrap_template": "Default Bootstrap.xml",
#         "hostname": "panos-81",
#         "auth_key": "v123",
#         "management_ip": "192.168.1.100",
#         "management_netmask": "255.255.255.0",
#         "management_gateway": "192.168.1.254",
#         "management_network": "mgmt",
#         "management_subnet": "mgmt-subnet",
#         "dns_server": "192.168.1.2",
#         "image_name": "panos-81.img",
#         "image_flavor": "m1.xlarge",
#         "outside_network": "outside",
#         "outside_subnet": "outside-subnet",
#         "outside_ip": "192.168.2.100",
#         "inside_network": "inside",
#         "inside_subnet": "inside-subnet",
#         "inside_ip": "192.168.3.100",
#         "ethernet2_1_profile": "PINGSSHTTPS",
#         "ethernet1_1_profile": "PINGSSHTTPS",
#         "default_next_hop": "10.10.10.10"
#     }
#     r = client.post('/debug_openstack_config', data=json.dumps(params), content_type='application/json')
#     print(r.data)
#     d = json.loads(r.data)
#     assert r.status_code == 200
#     assert d['openstack_config'] is not None
#     # assert d['openstack_config']['hostname'] == "panos-81"
#     assert d['success'] is True
#
#
# def test_build_base_configs(client):
#     """
#     Tests build base_configs
#     :param client: test client
#     :return: test assertions
#     """
#     params = {
#         "deployment_type": "openstack",
#         "hostname": "panos-81",
#         "auth_key": "v123",
#         "management_ip": "192.168.1.100",
#         "management_netmask": "255.255.255.0",
#         "management_gateway": "192.168.1.254",
#         "dns_server": "192.168.1.2",
#         "ethernet2_1_profile": "PINGSSHTTPS",
#         "ethernet1_1_profile": "PINGSSHTTPS",
#         "default_next_hop": "10.10.10.10"
#     }
#     r = client.post('/debug_base_config', data=json.dumps(params), content_type='application/json')
#     print(r.data)
#     d = json.loads(r.data)
#     assert d['success'] is True
#
#
# def test_build_openstack_configs(client):
#     """
#     Tests build openstack_configs
#     :param client: test client
#     :return: test assertions
#     """
#     params = {
#         "deployment_type": "openstack",
#         "hostname": "panos-81",
#         "auth_key": "v123",
#         "management_ip": "192.168.1.100",
#         "management_netmask": "255.255.255.0",
#         "management_gateway": "192.168.1.254",
#         "dns_server": "192.168.1.2",
#         "outside_ip": "192.168.2.100",
#         "inside_ip": "192.168.3.100",
#         "ethernet2_1_profile": "PINGSSHTTPS",
#         "ethernet1_1_profile": "PINGSSHTTPS",
#         "default_next_hop": "10.10.10.10"
#     }
#     r = client.post('/debug_openstack_config', data=json.dumps(params), content_type='application/json')
#     print(r.data)
#     d = json.loads(r.data)
#     assert d['success'] is True


def test_build_openstack_archive(client):
    """
    Tests build openstack_configs
    :param client: test client
    :return: test assertions
    """
    print("Test: Build Openstack Archive".center(79, '-'))

    params = {
        "deployment_type": "openstack",
        "hostname": "panos-81",
        "auth_key": "v123",
        "management_ip": "192.168.1.100",
        "management_netmask": "255.255.255.0",
        "management_gateway": "192.168.1.254",
        "dns_server": "192.168.1.2",
        "outside_ip": "192.168.2.100",
        "inside_ip": "192.168.3.100",
        "ethernet2_1_profile": "PINGSSHTTPS",
        "ethernet1_1_profile": "PINGSSHTTPS",
        "default_next_hop": "10.10.10.10"
    }
    r = client.post('/generate_bootstrap_package', data=json.dumps(params), content_type='application/json')
    assert r.status_code == 200


# def test_add_template_location(client):
#     """
#     Tests the api to add a template location to the configuration
#     :param client: test client
#     :return: test assertions
#     """
#     params = {
#         "name": "TEST_LOCATION",
#         "description": "ADDED BY PYTEST",
#         "type": "local",
#         "location": "templates/test/123"
#     }
#     r = client.post('/add_template_location', data=json.dumps(params), content_type='application/json')
#     assert r.status_code == 200
#
#
# def test_remove_template_location(client):
#     """
#     Tests the api to add a template location to the configuration
#     :param client: test client
#     :return: test assertions
#     """
#     params = {
#         "name": "TEST_LOCATION"
#     }
#     r = client.post('/remove_template_location', data=json.dumps(params), content_type='application/json')
#     assert r.status_code == 200


def test_get_bootstrap_variables(client):
    """
    Tests the api to retrieve the list of variables in the bootstrap.xml template
    :param client: test client
    :return: test assertions
    """
    print("Test: Get Template Variables".center(79, '-'))

    params = {
        "bootstrap_template": "Default bootstrap.xml"
    }
    r = client.post('/get_bootstrap_variables', data=json.dumps(params), content_type='application/json')
    assert r.status_code == 200
    d = json.loads(r.data)
    assert d['success'] is True
    assert d['payload'] is not None


def test_import_template(client):
    """
    Tests the api to import template files
    :param client: test client
    :return: test assertions
    """
    print("Test: Import Template".center(79, '-'))

    params = {
        "name": "TEST_IMPORT",
        "description": "ADDED BY PYTEST",
        "template": "ASDFDFLKSDF:LKSD:KLSDF:LKSFDLDS:LKSDF:LKSD:LKSD:FLKSDF:KLSD:F"
    }
    r = client.post('/import_template', data=json.dumps(params), content_type='application/json')
    assert r.status_code == 200
    d = json.loads(r.data)
    assert d['success'] is True


def test_get_template(client):
    """
    Tests the api to retrieve template files
    :param client: test client
    :return: test assertions
    """
    print("Test: Get Template".center(79, '-'))
    params = {
        "template_name": "TEST_IMPORT"
    }
    r = client.post('/get_template', data=json.dumps(params), content_type='application/json')
    print(r)
    assert r.status_code == 200
    assert b"ASDF" in r.data


def test_list_templates(client):
    """
    Tests the api to retrieve the list of templates. This will test listed all files that are present in the
    configuration as well as any files that are present in the import directory. Manually create a file on the
    filesystem and verify it shows up in the list. This allows the operator to import files on startup via
    docker volumes or ansible or whatever
    :param client: test client
    :return: test assertions
    """

    print("Test: List Templates".center(79, '-'))
    r = client.get('/list_templates')
    assert r.status_code == 200
    d = json.loads(r.data)
    assert d['success'] is True
    assert d['templates'] is not None

    # mow iter over all found templates and verify we have all we need here (imported and manually created)
    found_import = False
    for t in d['templates']:
        if t['name'] == 'TEST_IMPORT':
            found_import = True

    print(d)
    assert found_import is True


def test_delete_template(client):
    """
    Tests the api to delete template files
    :param client: test client
    :return: test assertions
    """

    print("Test: Delete Template".center(79, '-'))
    params = {
        "template_name": "TEST_IMPORT"
    }
    r = client.post('/delete_template', data=json.dumps(params), content_type='application/json')
    assert r.status_code == 200
    d = json.loads(r.data)
    assert d['success'] is True

    # also delete our manually created file as well
    params = {
        "template_name": "MANUAL_IMPORT"
    }
    m = client.post('/delete_template', data=json.dumps(params), content_type='application/json')
    assert m.status_code == 200


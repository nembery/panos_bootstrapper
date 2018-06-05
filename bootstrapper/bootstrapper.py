#!/usr/bin/env python

from flask import Flask
from flask import abort
from flask import jsonify
from flask import render_template
from flask import request
from flask import send_file

from lib import archive_utils
from lib import bootstrapper_utils
from lib import cache_utils
from lib import openstack_utils

app = Flask(__name__)
defaults = bootstrapper_utils.load_defaults()
config = bootstrapper_utils.load_config()


@app.route('/')
def index():
    return render_template('index.html', title='Bootstrapper')


@app.route('/api/v0.1/get_object', methods=['POST'])
def get_object():
    posted_json = request.get_json(force=True)
    key = posted_json.get('key', None)
    if key is None:
        return jsonify(message="Not all required keys are present", success=False, status_code=400)

    contents = cache_utils.get(key)
    return jsonify(key=key, contents=contents)


@app.route('/api/v0.1/set_object', methods=['POST'])
def set_object():
    posted_json = request.get_json(force=True)
    contents = posted_json.get('contents', None)
    if contents is None:
        return jsonify(message="Not all required keys are present", success=False, status_code=400)

    key = cache_utils.set(contents)
    return jsonify(key=key, success=True)


def _build_base_configs(posted_json):
    common_required_keys = {'hostname', 'auth_key',
                            'management_ip', 'management_mask', 'management_gateway', 'dns_server'}

    if not common_required_keys.issubset(posted_json):
        print 'Not all required keys are present for build_base_config!!'
        abort(400, 'Not all required keys are present')

    init_cfg_contents = render_template('panos/init-cfg.txt', **posted_json)
    init_cfg_key = cache_utils.set(init_cfg_contents)

    authcode = render_template('panos/authcodes', **posted_json)
    authcode_key = cache_utils.set(authcode)

    bootstrap_config = bootstrapper_utils.generate_config(defaults, posted_json)

    print 'checking bootstrap required_variables'
    if not bootstrapper_utils.verify_data(bootstrap_config):
        abort(400, 'Not all required keys for bootstrap.xml are present')

    bootstrap_xml = render_template('panos/bootstrap.xml', **bootstrap_config)

    bs_key = cache_utils.set(bootstrap_xml)

    base_config = dict()

    base_config['bootstrap.xml'] = dict()
    base_config['bootstrap.xml']['key'] = bs_key
    base_config['bootstrap.xml']['archive_path'] = 'config'
    base_config['bootstrap.xml']['url'] = config["base_url"] + '/api/v0.1/get/' + bs_key

    base_config['init-cfg.txt'] = dict()
    base_config['init-cfg.txt']['key'] = init_cfg_key
    base_config['init-cfg.txt']['archive_path'] = 'config'
    base_config['init-cfg.txt']['url'] = config["base_url"] + '/api/v0.1/get/' + init_cfg_key

    base_config['authcodes'] = dict()
    base_config['authcodes']['key'] = authcode_key
    base_config['authcodes']['archive_path'] = 'license'
    base_config['authcodes']['url'] = config["base_url"] + '/api/v0.1/get/' + init_cfg_key

    return base_config


def _build_openstack_heat(base_config, posted_json, archive=False):
    if not openstack_utils.verify_data(posted_json):
        abort(400, "Not all required keys for openstack are present")

    # create the openstack config object that will be used to populate the HEAT template
    openstack_config = openstack_utils.generate_config(defaults, posted_json)
    if archive:
        # the rendered heat template should reference local files that will be included in the archive
        openstack_config['init_cfg'] = 'init-cfg.txt'
        openstack_config['bootstrap_xml'] = 'bootstrap.xml'
        openstack_config['authcodes'] = 'authcodes'
    else:
        openstack_config['init_cfg'] = base_config['init-cfg.txt']['url']
        openstack_config['bootstrap_xml'] = base_config['bootstrap.xml']['url']
        openstack_config['authcodes'] = base_config['authcodes']['url']

    heat_env = render_template('openstack/heat-environment.yaml', **openstack_config)
    heat = render_template('openstack/heat.yaml', **base_config)

    he_key = cache_utils.set(heat_env)
    h_key = cache_utils.set(heat)

    base_config['heat-environment.yaml'] = dict()
    base_config['heat-environment.yaml']['key'] = he_key
    base_config['heat-environment.yaml']['archive_path'] = '.'

    base_config['heat-template.yaml'] = dict()
    base_config['heat-template.yaml']['key'] = h_key
    base_config['heat-template.yaml']['archive_path'] = '.'

    return base_config


@app.route('/api/v0.1/debug_base_config', methods=['POST'])
def debug_base_config():
    posted_json = request.get_json(force=True)
    base_config = _build_base_configs(posted_json)
    return jsonify(message="Base Config built", success=True, status_code=200)


@app.route('/api/v0.1/debug_openstack_config', methods=['POST'])
def debug_openstack_cnfig():
    posted_json = request.get_json(force=True)
    base_config = _build_base_configs(posted_json)
    openstack_config = _build_openstack_heat(base_config, posted_json)
    print openstack_config
    return jsonify(message="Openstack Config built", success=True, status_code=200)


@app.route('/api/v0.1/generate_openstack_archive', methods=['POST'])
def generate_openstack_archive():
    posted_json = request.get_json(force=True)
    base_config = _build_base_configs(posted_json)
    base_config = _build_openstack_heat(base_config, posted_json, archive=True)
    if 'hostname' not in posted_json:
        abort(400, 'No hostname found in posted data')

    zipfile = archive_utils.create_archive(base_config, posted_json['hostname'])
    print 'zipfile path is: %s' % zipfile
    if zipfile is None:
        abort(500, 'Could not create archive! Check bootstrapper logs for more information')

    return send_file(zipfile)


@app.route('/api/v0.1/generate_kvm_iso', methods=['POST'])
def generate_kvm_iso():
    posted_json = request.get_json(force=True)
    base_config = _build_base_configs(posted_json)
    if 'hostname' not in posted_json:
        abort(400, 'No hostname found in posted data')

    iso_image = archive_utils.create_iso(base_config, posted_json['hostname'])
    print 'iso path is: %s' % iso_image
    if iso_image is None:
        abort(500, 'Could not create ISO Image! Check bootstrapper logs for more information')

    return send_file(iso_image)


@app.route('/api/v0.1/build_bootstrap', methods=['POST'])
def build_bootstrap():
    posted_json = request.get_json(force=True)
    deployment_type = posted_json.get('deployment_type', None)
    if deployment_type is None:
        return jsonify(message="No deployment_type set", success=False, status_code=400)

    if deployment_type not in ['openstack', 'vmware', 'aws']:
        return jsonify(message="unknown deployment_type!", success=False, status_code=400)

    common_required_keys = {'hostname', 'auth_key',
                            'management_ip', 'management_mask', 'management_gateway', 'dns_server'}

    if not common_required_keys.issubset(posted_json):
        return jsonify(message="Not all required keys are present", success=False, status_code=400)

    defaults = bootstrapper_utils.load_defaults()
    config = bootstrapper_utils.load_config()

    init_cfg_contents = render_template('panos/init-cfg.txt', **posted_json)
    init_cfg_key = cache_utils.set(init_cfg_contents)
    bootstrap_config = bootstrapper_utils.generate_config(defaults, posted_json)

    print 'checking bootstrap required_variables'
    if not bootstrapper_utils.verify_data(bootstrap_config):
        return jsonify(message="Not all required keys for bootstrap.xml are present", success=False, status_code=400)

    bootstrap_xml = render_template('panos/bootstrap.xml', **bootstrap_config)

    bs_key = cache_utils.set(bootstrap_xml)

    base_config = dict()
    init_cfg_url = config["base_url"] + '/api/v0.1/get/' + init_cfg_key
    bs_url = config["base_url"] + '/api/v0.1/get/' + bs_key

    base_config['bootstrap_url'] = bs_url
    base_config['init_cfg_url'] = init_cfg_url

    if deployment_type == 'openstack':
        if not openstack_utils.verify_data(posted_json):
            return jsonify(message="Not all required keys for openstack are present", success=False, status_code=400)

        # create the openstack config object that will be used to populate the HEAT template
        openstack_config = openstack_utils.generate_config(defaults, posted_json)

        # append the base configuration things
        openstack_config.update(base_config)

        heat_env = render_template('openstack/heat-environment.yaml', **openstack_config)
        heat = render_template('openstack/heat.yaml', **openstack_config)

        he_key = cache_utils.set(heat_env)
        h_key = cache_utils.set(heat)

        return jsonify(success=True, init_cfg_key=init_cfg_key, bs_key=bs_key, openstack_config=openstack_config,
                       he_key=he_key, h_key=h_key)

    return jsonify(success=False, message="unknown deployment options")


@app.route('/api/v0.1/add_template_location', methods=['POST'])
def add_template_location():
    """
    Adds a template location to the configuration
    :return: json with 'success', 'message' and 'status' keys
    """
    posted_json = request.get_json(force=True)
    try:
        name = posted_json['name']
        location = posted_json['location']
        description = posted_json.get('description', 'template repository')
        repo_type = posted_json.get('type', 'local')

    except KeyError:
        print 'Not all required keys are present!'
        return jsonify(message="Not all required keys for add template are present", success=False, status_code=400)

    loaded_config = bootstrapper_utils.load_config()

    if 'template_locations' not in loaded_config:
        print 'invalid configuration found, hmmm...'
        loaded_config['template_locations'] = list()

    new_repo = dict()
    new_repo['name'] = name
    new_repo['location'] = location
    new_repo['description'] = description
    new_repo['type'] = repo_type

    for location in loaded_config['template_locations']:
        if location['name'] == name and location['type'] == repo_type:
            return jsonify(success=True, message='template repository already exists in configuration', status_code=200)

    loaded_config['template_locations'].append(new_repo)
    if bootstrapper_utils.save_config(loaded_config):
        return jsonify(success=True, message='Added template repository to the configuration', status_code=200)
    else:
        return jsonify(success=False, message='Could not add template repository to the configuration', status_code=500)


@app.route('/api/v0.1/remove_template_location', methods=['POST'])
def remove_template_location():
    """
    Removes a template location from the configuration
    :return: json with 'success', 'message' and 'status' keys
    """
    posted_json = request.get_json(force=True)
    try:
        name = posted_json['name']

    except KeyError:
        print 'Not all required keys are present!'
        return jsonify(message="Not all required keys for add template are present", success=False, status_code=400)

    loaded_config = bootstrapper_utils.load_config()

    if 'template_locations' not in loaded_config:
        print 'invalid configuration found, hmmm...'
        return jsonify(message="Invalid Configuration found!", success=False, status_code=500)

    found = False
    for location in loaded_config['template_locations']:
        if location['name'] == name:
            found = True
            loaded_config['template_locations'].remove(location)
            break

    if found:
        if bootstrapper_utils.save_config(loaded_config):
            return jsonify(success=True, message='Removed template repository from the configuration', status_code=200)
        else:
            return jsonify(success=False, message='Could not remove template repository!', status_code=500)

    return jsonify(success=True, message='Removed template repository from the configuration', status_code=200)


@app.route('/api/v0.1/get_bootstrap_variables', methods=['GET'])
def get_bootstrap_variables():
    vs = bootstrapper_utils.get_bootstrap_variables()
    return jsonify(success=True, variables=vs, status_code=200)


@app.route('/api/v0.1/import_template', methods=['POST'])
def import_template():
    """
    Adds a template location to the configuration
    :return: json with 'success', 'message' and 'status' keys
    """
    posted_json = request.get_json(force=True)
    try:
        name = posted_json['name']
        template = posted_json['template']
        description = posted_json.get('description', 'Imported Template')

    except KeyError:
        print 'Not all required keys are present!'
        return jsonify(message="Not all required keys for add template are present", success=False, status_code=400)

    if bootstrapper_utils.import_template(template, name, description):
        return jsonify(success=True, message='Imported Template Successfully', status_code=200)
    else:
        return jsonify(success=False, message='Could not import template repository to the configuration',
                       status_code=500)


@app.route('/api/v0.1/delete_template', methods=['POST'])
def delete_template():
    """
    Adds a template location to the configuration
    :return: json with 'success', 'message' and 'status' keys
    """
    posted_json = request.get_json(force=True)
    try:
        name = posted_json['name']
    except KeyError:
        print 'Not all required keys are present!'
        return jsonify(message="Not all required keys for add template are present", success=False, status_code=400)

    if bootstrapper_utils.delete_imported_template(name):
        return jsonify(success=True, message='Deleted Template Successfully', status_code=200)
    else:
        return jsonify(success=False, message='Could not delete template', status_code=500)


@app.route('/api/v0.1/list_templates', methods=['GET'])
def list_templates():
    ts = bootstrapper_utils.list_templates()
    return jsonify(success=True, templates=ts, status_code=200)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

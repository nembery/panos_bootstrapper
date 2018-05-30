import os

import jinja2
import yaml
from flask import Flask
from flask import g
from jinja2 import FileSystemLoader
from jinja2 import meta

app = Flask(__name__)


def get_bootstrap_template():
    config = load_config()
    default = config.get('default_template', 'Default')
    for tl in config.get('template_locations', ()):
        print 'checking %s' % tl['name']
        if tl["name"] == default:
            bootstrap_template = tl['location'] + '/bootstrap.xml'
            return bootstrap_template

    print 'OH NO! Returning default location'
    return 'templates/panos/bootstrap.xml'


def load_defaults():
    with open(os.path.join(app.root_path, '../conf/defaults.yaml')) as config_file:
        defaults = yaml.load(config_file.read())

    return defaults


def load_config():
    with app.app_context():
        config = getattr(g, 'bootstrap_config', None)
        if config is None:
            with open(os.path.join(app.root_path, '../conf/configuration.yaml')) as config_file:
                config = yaml.load(config_file.read())

        return config


def save_config(new_config):
    try:
        with open(os.path.join(app.root_path, '../conf/configuration.yaml'), 'w') as config_file:
            config_object = yaml.dump(new_config, default_flow_style=False)
            config_file.write(config_object)
            with app.app_context():
                g.bootstrap_config = config_object

    except OSError:
        print 'Could not save new configuration!'
        return False

    return True


def __get_template(template_path):
    app_root_path = os.path.abspath(os.path.join(app.root_path, '..'))
    env = jinja2.Environment(loader=FileSystemLoader(app_root_path))
    return env.get_template(template_path)


def __get_required_vars_from_template(template_path):
    """
    Parse the template and return a list of all the variables defined therein
    template path is usually something like 'templates/panos/bootstrap.xml'
    :param template_path: relative path to the application root to a jinja2 template
    :return: set of variable named defined in the template
    """
    app_root_path = os.path.abspath(os.path.join(app.root_path, '..'))
    env = jinja2.Environment(loader=FileSystemLoader(app_root_path))
    template = env.loader.get_source(env, template_path)
    ast = env.parse(template)
    return meta.find_undeclared_variables(ast)


def verify_data(available_vars):
    """
    Verify all the required variables have been posted from the user
    :param available_vars: dict of all available variables from the posted data and also the defaults
    :return:
    """
    template_path = get_bootstrap_template()
    vs = __get_required_vars_from_template(template_path)
    print vs
    for r in vs:
        print 'checking var: %s' % r
        if r not in available_vars:
            print 'template variable %s is not defined!!' % r
            return False

    return True


def get_bootstrap_variables():
    """
    Returns a list of all configured variables in the bootstrap.xml template
    :param posted_json:
    :return:
    """
    template_path = get_bootstrap_template()
    vs = __get_required_vars_from_template(template_path)
    available_variables = list()
    for r in vs:
        available_variables.append(r)

    return available_variables


def generate_config(defaults, posted_json):
    template_path = get_bootstrap_template()
    bootstrap_config = {}
    # populate with defaults if they exist
    if 'bootstrap' in defaults:
        bootstrap_config.update(defaults['bootstrap'])

    defined_vars = __get_required_vars_from_template(template_path)
    # push all the required keys - should have already been validated
    for k in defined_vars:
        bootstrap_config[k] = posted_json.get(k, None)

    # push all the optional keys if they exist
    for k in defined_vars:
        if k in posted_json:
            bootstrap_config[k] = posted_json[k]

    return bootstrap_config


import os

import jinja2
import yaml
from flask import Flask
from jinja2 import FileSystemLoader
from jinja2 import meta


def load_defaults():
    app = Flask(__name__)

    with open(os.path.join(app.root_path, '../conf/defaults.yaml')) as config_file:
        defaults = yaml.load(config_file.read())

    return defaults


def load_config():
    app = Flask(__name__)

    with open(os.path.join(app.root_path, '../conf/configuration.yaml')) as config_file:
        config = yaml.load(config_file.read())

    return config


def __get_template(template_path):
    app = Flask(__name__)
    app_root_path = os.path.abspath(os.path.join(app.root_path, '..'))
    env = jinja2.Environment(loader=FileSystemLoader(app_root_path))
    return env.get_template(template_path)


def __get_required_vars_from_template(template_path):
    """
    Parse the template and return a list of all the variables defined therein
    template path is usually something like 'templates/bootstrap.xml'
    :param template_path: relative path to the application root to a jinja2 template
    :return: set of variable named defined in the template
    """
    app = Flask(__name__)
    app_root_path = os.path.abspath(os.path.join(app.root_path, '..'))
    env = jinja2.Environment(loader=FileSystemLoader(app_root_path))
    template = env.loader.get_source(env, template_path)
    ast = env.parse(template)
    return meta.find_undeclared_variables(ast)


def verify_data(posted_json):
    """
    Verify all the required variables have been posted from the user
    :param posted_json:
    :return:
    """
    template_path = 'templates/bootstrap.xml'
    vs = __get_required_vars_from_template(template_path)
    print vs
    for r in vs:
        print 'checking var: %s' % r
        if r not in posted_json:
            print 'template variable %s is not defined!!' % r
            return False

    return True


def generate_config(defaults, posted_json):
    template_path = 'templates/bootstrap.xml'
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

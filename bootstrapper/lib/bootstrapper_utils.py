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
            try:
                with open(os.path.join(app.root_path, '../conf/configuration.yaml')) as config_file:
                    config = yaml.load(config_file.read())

                if type(config) is not dict:
                    print 'Unknown config object from configuration.yaml'
                    config = dict()

                if 'template_locations' not in config:
                    print 'invalid configuration found, hmmm...'
                    config['template_locations'] = list()

                g.bootstrap_config = config
                
                # with open(os.path.join(app.root_path, '../conf/templates.yaml')) as template_config_file:
                #     template_config_object = yaml.load(template_config_file.read())
                #
                #     if 'template_locations' in template_config_object:
                #         config['template_locations'] = template_config_object['template_locations']
                #
                #     else:
                #         print 'Invalid template configuration file at templates.yaml'

            except yaml.scanner.ScannerError:
                print 'Could not load configuration files!'
                raise

        return config


def save_config(new_config):
    try:
        with open(os.path.join(app.root_path, '../conf/configuration.yaml'), 'w') as config_file:
            config_object = yaml.safe_dump(new_config, default_flow_style=False)
            config_file.write(config_object)
            with app.app_context():
                g.bootstrap_config = config_object

    except OSError:
        print 'Could not save new configuration!'
        return False

    return True


def import_template(template, file_name, description):
    """
    Imports a template into the templates/imports directory and saves the metadata into the app config
    :param template: string of the template text
    :param file_name: name of the file to save
    :param description: description to save in the configured templates

    :return: boolean
    """

    loaded_config = load_config()

    new_import = dict()
    new_import['name'] = file_name
    new_import['location'] = 'templates/import'
    new_import['description'] = description
    new_import['type'] = 'local'

    for location in loaded_config['template_locations']:
        if location['name'] == file_name and location['type'] == 'local':
            print 'A template with this name already exists'
            return True

    rel_import_directory = loaded_config.get('template_import_directory', 'templates/import')
    import_directory = os.path.abspath(os.path.join(app.root_path, '..', rel_import_directory))

    print rel_import_directory

    try:
        if not os.path.exists(import_directory):
            print 'Creating import directory'
            os.makedirs(import_directory)

        with open(os.path.join(import_directory, '%s' % file_name), 'w+') as template_file:
            print 'WRITING TEMPLATE'
            print os.path.join(import_directory, '%s' % file_name)
            unescaped_template = unescape(template)
            template_file.write(unescaped_template)

    except OSError:
        print 'Could not save new template!'
        return False

    loaded_config['template_locations'].append(new_import)
    if not save_config(loaded_config):
        print 'Could not save new configuration with imported template!'
        return False

    return True


def delete_imported_template(file_name):
    """
    Deletes an imported template
    :param file_name: name of the file to save
    :return: boolean
    """

    loaded_config = load_config()

    rel_import_directory = loaded_config.get('template_import_directory', 'templates/import')
    import_directory = os.path.abspath(os.path.join(app.root_path, '..', rel_import_directory))

    print rel_import_directory

    try:
        if not os.path.exists(import_directory):
            print 'Invalid Configuration!'
            return False

        template_file = os.path.join(import_directory, '%s' % file_name)
        if os.path.exists(template_file):
            os.remove(template_file)

    except OSError:
        print 'Could not delete template!'
        return False

    found = False
    for location in loaded_config['template_locations']:
        if location['name'] == file_name and location['type'] == 'local':
            found = True
            loaded_config['template_locations'].remove(location)
            break

    if found:
        if not save_config(loaded_config):
            print 'Could not save configuration after delete!'
            return False

    return True


def list_templates():
    """
    List all templates that are available for use by bootstrapper utility

    :return: list of template dict objects
    """
    loaded_config = load_config()

    rel_import_directory = loaded_config.get('template_import_directory', 'templates/import')
    import_directory = os.path.abspath(os.path.join(app.root_path, '..', rel_import_directory))
    all_imported_files = os.listdir(import_directory)

    print all_imported_files

    all_templates = loaded_config['template_locations']

    file_already_configured = False
    for file_name in all_imported_files:
        for location in loaded_config['template_locations']:
            if location['name'] == file_name and location['type'] == 'local':
                print 'A template with this name already exists'
                file_already_configured = True
                break

        if not file_already_configured:
            print 'adding new file to list %s' % file_name
            new_import = dict()
            new_import['name'] = file_name
            new_import['location'] = 'templates/import'
            new_import['description'] = 'Discovered Import'
            new_import['type'] = 'local'
            all_templates.append(new_import)

    return all_templates


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

    # FIXME - we will always need these ?
    init_cfg_path = 'templates/panos/init-cfg.txt'
    authcodes_path = 'templates/panos/authcodes'

    init_cfg_vars = __get_required_vars_from_template(init_cfg_path)
    authcodes_vars = __get_required_vars_from_template(authcodes_path)

    vs = __get_required_vars_from_template(template_path)
    available_variables = list()

    for b in vs:
        available_variables.append(b)
    for i in init_cfg_vars:
        available_variables.append(i)
    for a in authcodes_vars:
        available_variables.append(a)

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


def unescape(s):
    """
    :param s: String - string that should be have html entities removed
    :return: string with html entities removed
    """
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&amp;", "&")
    s = s.replace("&quot;", '"')
    s = s.replace("&#39;", "'")
    s = s.replace("\\n", "\n")
    return s
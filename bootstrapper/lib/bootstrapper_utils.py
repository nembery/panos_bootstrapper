import os

import jinja2
import yaml
from flask import Flask
from flask import g
from jinja2 import FileSystemLoader
from jinja2 import meta

from bootstrapper.lib.db import db_session
from bootstrapper.lib.db_models import Template

app = Flask(__name__)


def get_bootstrap_template():
    config = load_config()
    print('config is %s' % config)
    default = config.get('default_template', 'Default')
    for tl in config.get('template_locations', {}):
        name = tl.get('name', '')
        print(f"checking {name}")
        if name == default:
            bootstrap_template = tl['location'] + '/bootstrap.xml'
            return bootstrap_template

    print("OH NO! Returning default location")
    return 'templates/panos/bootstrap.xml'


def get_bootstrap_template_old():
    config = load_config()
    print('config is %s' % config)
    default = config.get('default_template', 'Default')
    for tl in config.get('template_locations', {}):
        name = tl.get('name', '')
        print(f"checking {name}")
        if name == default:
            bootstrap_template = tl['location'] + '/bootstrap.xml'
            return bootstrap_template

    print("OH NO! Returning default location")
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
                    print("Unknown config object from configuration.yaml")
                    config = dict()

                if 'template_locations' not in config:
                    print("invalid configuration found, hmmm...")
                    config['template_locations'] = list()

                g.bootstrap_config = config

                # with open(os.path.join(app.root_path, '../conf/templates.yaml')) as template_config_file:
                #     template_config_object = yaml.load(template_config_file.read())
                #
                #     if 'template_locations' in template_config_object:
                #         config['template_locations'] = template_config_object['template_locations']
                #
                #     else:
                #         print("Invalid template configuration file at templates.yaml")

            except yaml.scanner.ScannerError:
                print("Could not load configuration files!")
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
        print("Could not save new configuration!")
        return False

    return True


def import_template(template, file_name, description, template_type='bootstrap'):
    """
    Imports a template into the templates/imports directory and saves the metadata into the app config
    :param template: string of the template text
    :param file_name: name of the file to save
    :param description: description to save in the configured templates

    :return: boolean
    """
    t = Template.query.filter(Template.name == file_name).first()

    if t is None:
        print('Adding new record to db')
        unescaped_template = unescape(template)
        t = Template(name=file_name, description=description, template=unescaped_template, type=template_type)
        db_session.add(t)
        db_session.commit()

    else:
        print('template exists in db')

    return True


def import_template_OLD(template, file_name, description):
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
            print("A template with this name already exists")
            return True

    rel_import_directory = loaded_config.get('template_import_directory', 'templates/import')
    import_directory = os.path.abspath(os.path.join(app.root_path, '..', rel_import_directory))

    print(rel_import_directory)

    try:
        if not os.path.exists(import_directory):
            print("Creating import directory")
            os.makedirs(import_directory)

        with open(os.path.join(import_directory, '%s' % file_name), 'w+') as template_file:
            print("WRITING TEMPLATE")
            print(os.path.join(import_directory, '%s' % file_name))
            unescaped_template = unescape(template)
            template_file.write(unescaped_template)

    except OSError:
        print("Could not save new template!")
        return False

    loaded_config['template_locations'].append(new_import)
    if not save_config(loaded_config):
        print("Could not save new configuration with imported template!")
        return False

    print('Checking DB')
    t = Template.query.filter(Template.name == file_name).first()

    if t is None:
        print('Adding new record to db')
        unescaped_template = unescape(template)
        t = Template(name=file_name, description=description, template=unescaped_template, type='bootstrap')
        db_session.add(t)
        db_session.commit()

    else:
        print('template exists in db')

    return True


def delete_template(file_name):
    """
    Deletes an imported template
    :param file_name: name of the file to save
    :return: boolean
    """
    t = Template.query.filter(Template.name == file_name).first()

    if t is not None:
        db_session.delete(t)
        db_session.commit()

    return True


def list_bootstrap_templates():
    """
    List all templates that are available for use by bootstrapper utility

    :return: list of template dict objects
    """
    all_templates = list()
    default_template = dict()
    default_template['name'] = 'None'
    default_template['description'] = 'No Bootstrap.xml Required'
    default_template['type'] = 'bootstrap'
    all_templates.append(default_template)

    db_templates = Template.query.filter(Template.type == 'bootstrap')
    for t in db_templates:
        db_template = dict()
        db_template['name'] = t.name
        db_template['description'] = t.description
        db_template['type'] = t.type
        all_templates.append(db_template)

    return all_templates


def list_init_cfg_templates():
    """
    List all templates that are available for use by bootstrapper utility

    :return: list of template dict objects
    """
    all_templates = list()

    db_templates = Template.query.filter(Template.type == 'init-cfg')
    for t in db_templates:
        db_template = dict()
        db_template['name'] = t.name
        db_template['description'] = t.description
        db_template['type'] = t.type
        all_templates.append(db_template)

    return all_templates


def __get_template(template_path):
    app_root_path = os.path.abspath(os.path.join(app.root_path, '..'))
    env = jinja2.Environment(loader=FileSystemLoader(app_root_path))
    return env.get_template(template_path)


def __get_required_vars_from_template(template_name):
    """
    Parse the template and return a list of all the variables defined therein
    template path is usually something like 'templates/panos/bootstrap.xml'
    :param template_path: relative path to the application root to a jinja2 template
    :return: set of variable named defined in the template
    """

    t = Template.query.filter(Template.name == template_name).first()

    if t is None:
        print('Could not load template %s' % template_name)
        return set()

    else:
        print('Got a template, lets go')

    #app_root_path = os.path.abspath(os.path.join(app.root_path, '..'))
    #env = jinja2.Environment(loader=FileSystemLoader(app_root_path))
    #template = env.loader.get_source(env, template_path)

    print(t.template)
    env = jinja2.Environment()
    ast = env.parse(t.template)
    print(ast)
    return meta.find_undeclared_variables(ast)


def verify_data(available_vars):
    """
    Verify all the required variables have been posted from the user
    :param available_vars: dict of all available variables from the posted data and also the defaults
    :return:
    """
    template_path = get_bootstrap_template()
    vs = __get_required_vars_from_template(template_path)
    print(vs)
    for r in vs:
        print("checking var: %s" % r)
        if r not in available_vars:
            print("template variable %s is not defined!!" % r)
            return False

    return True


def get_bootstrap_variables(requested_templates):
    """
    Returns a list of all configured variables in the bootstrap.xml template
    :param requested_templates: dict containing at least the following keys: 'bootstrap_template', 'init_cfg_templates'
    :return: list of variables defined in all requested templates
    """

    print('getting bootstrap variables')
    available_variables = list()

    init_cfg_name = requested_templates.get('init_cfg_template', 'init-cfg-static.txt')
    bootstrap_name = requested_templates.get('bootstrap_template', None)

    init_cfg_vars = __get_required_vars_from_template(init_cfg_name)
    for i in init_cfg_vars:
        available_variables.append(i)

    if bootstrap_name != "None" or bootstrap_name is not None:
        vs = __get_required_vars_from_template(bootstrap_name)
        for b in vs:
            available_variables.append(b)

    return available_variables


def generate_boostrap_config_with_defaults(defaults, configuration_parameters):
    """
    Generates a dict of context parameters pre-seeded with defaults form the conf/defaults.yaml file
    :param defaults:  object from the defaults.yaml file
    :param configuration_parameters: params supplied to the bootstrapper service via JSON POST
    :return: dict of context parameters
    """

    if 'bootstrap_template_name' in configuration_parameters:
        bootstrap_template_name = configuration_parameters['bootstrap_template']
    else:
        config = load_config()
        bootstrap_template_name = config.get('default_template', 'Default')

    bootstrap_config = {}
    # populate with defaults if they exist
    if 'bootstrap' in defaults:
        bootstrap_config.update(defaults['bootstrap'])

    defined_vars = __get_required_vars_from_template(bootstrap_template_name)
    # push all the required keys - should have already been validated
    for k in defined_vars:
        bootstrap_config[k] = configuration_parameters.get(k, None)

    # push all the optional keys if they exist
    # for k in defined_vars:
    #     if k in configuration_parameters:
    #         bootstrap_config[k] = configuration_parameters[k]

    return bootstrap_config


def import_templates():
    """
    Ensures all default and imported templates exist in the template table
    :return: None
    """
    loaded_config = load_config()

    config = load_config()
    print('config is %s' % config)
    default_bootstrap_name = config.get('default_template', 'Default')

    default = Template.query.filter(Template.name == default_bootstrap_name).first()
    if default is None:
        print('Importing default bootstrap.xml files')
        default_file_path = os.path.abspath(os.path.join(app.root_path, '..', 'templates/panos/bootstrap.xml'))
        try:
            with open(default_file_path, 'r') as dfpf:
                t = Template(name=default_bootstrap_name,
                             description='Default Bootstrap template',
                             template=dfpf.read(),
                             type='bootstrap')

            db_session.add(t)
            db_session.commit()
        except OSError:
            print('Could not open file for importing')

    init_cfg_static = Template.query.filter(Template.name == 'Default Init-Cfg Static').first()
    if init_cfg_static is None:
        print('Importing default init-cfg-static')
        ics_file_path = os.path.abspath(os.path.join(app.root_path, '..', 'templates/panos/init-cfg-static.txt'))
        try:
            with open(ics_file_path, 'r') as icsf:
                i = Template(name='Default Init-Cfg Static',
                             description='Init-Cfg with static management IP addresses',
                             template=icsf.read(),
                             type='init-cfg')

                db_session.add(i)
                db_session.commit()
        except OSError:
            print('Could not open file for importing')

    init_cfg_dhcp = Template.query.filter(Template.name == 'Default Init-Cfg DHCP').first()
    if init_cfg_dhcp is None:
        print('Importing default init-cfg-dhcp')
        icd_file_path = os.path.abspath(os.path.join(app.root_path, '..', 'templates/panos/init-cfg-dhcp.txt'))
        try:
            with open(icd_file_path, 'r') as icdf:
                i = Template(name='Default Init-Cfg DHCP',
                             description='Init-Cfg with static management IP addresses',
                             template=icdf.read(),
                             type='init-cfg')

                db_session.add(i)
                db_session.commit()
        except OSError:
            print('Could not open file for importing')

    rel_import_directory = loaded_config.get('template_import_directory', 'templates/import/bootstrap')
    import_directory = os.path.abspath(os.path.join(app.root_path, '..', rel_import_directory))
    all_imported_files = os.listdir(import_directory)

    print('Importing bootstrap templates')
    for it in all_imported_files:
        t = Template.query.filter(Template.name == it).first()
        if t is None:
            try:
                with open(os.path.join(import_directory, it), 'r') as tf:
                    t = Template(name=it,
                                 description="Imported Template",
                                 template=tf.read(),
                                 type='bootstrap')
                    db_session.add(t)
                    db_session.commit()
            except OSError:
                print('Could not import bootstrap template!')

    # FIXME - add init-cfg importing as well (as soon as we need it)


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

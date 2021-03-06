import os

import jinja2
import yaml
from flask import Flask
from flask import g
from flask import render_template
from flask import render_template_string
from jinja2 import meta
from jinja2 import TemplateSyntaxError
from sqlalchemy.exc import SQLAlchemyError

from bootstrapper.lib import cache_utils
from bootstrapper.lib import openstack_utils
from bootstrapper.lib.db import db_session
from bootstrapper.lib.db_models import Template
from bootstrapper.lib.exceptions import RequiredParametersError
from bootstrapper.lib.exceptions import TemplateNotFoundError
from bootstrapper.lib.exceptions import InvalidConfigurationError

app = Flask(__name__)


def load_defaults():
    """
    Loads the defatult configuration values from a local file. This allows an operator to pre-load some defaults
    for jinja variable interpolation. This may be useful to customize behaviour of this service without modifying
    code and without exposing those defaults to a UI of client interface
    See the bootstrapper/conf/defaults.yaml for examples.

    The UI or client interface can always overwrite these!  To always enforce options just hard code them into
    the template directly

    :return: dict containing default values
    """
    with app.app_context():
        defaults = getattr(g, 'bootstrap_config', None)
        if defaults is None:
            try:
                with open(os.path.join(app.root_path, '../conf/defaults.yaml')) as config_file:
                    defaults = yaml.load(config_file.read())
            except yaml.scanner.ScannerError:
                print("Could not load defaults!")
                raise InvalidConfigurationError('Could not parse defaults configuration file')

        return defaults


def load_config():
    """
    Loads and caches the bootstrapper service configuration from the bootstrapper/conf/configuration.yaml file
    :return: dict containing all configuration options
    """
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

            except yaml.scanner.ScannerError:
                print("Could not load configuration files!")
                raise InvalidConfigurationError('Could not load configuration')

        return config


def import_template(template, template_name, description, template_type='bootstrap'):
    """
    Imports a template into the templates/imports directory and saves the metadata into the app config
    :param template: string of the template text
    :param template_name: name of the file to save
    :param description: description to save in the configured templates
    :param template_type: type of the template to save. Enum with options 'bootstrap', 'init-cfg', and 'config-snippet'

    :return: boolean
    """
    try:
        t = Template.query.filter(Template.name == template_name).first()

        if t is None:
            print('Adding new record to db')
            unescaped_template = unescape(template)
            t = Template(name=template_name, description=description, template=unescaped_template, type=template_type)
            db_session.add(t)
            db_session.commit()

        else:
            print('template exists in db')

        return True
    except SQLAlchemyError as sqe:
        print('Could not import file')
        print(str(sqe))
        return False


def delete_template(file_name):
    """
    Deletes an imported template
    :param file_name: name of the file to save
    :return: boolean
    """
    try:
        t = Template.query.filter(Template.name == file_name).first()

        if t is not None:
            db_session.delete(t)
            db_session.commit()

        return True
    except SQLAlchemyError as sqe:
        print('Could not delete template!')
        print(sqe)
        return False


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

    try:
        db_templates = Template.query.filter(Template.type == 'bootstrap')
        for t in db_templates:
            db_template = dict()
            db_template['name'] = t.name
            db_template['description'] = t.description
            db_template['type'] = t.type
            all_templates.append(db_template)

    except SQLAlchemyError as sqe:
        print('Could not list bootstrap templates')
        print(sqe)
    finally:
        return all_templates


def list_init_cfg_templates():
    """
    List all templates that are available for use by bootstrapper utility

    :return: list of template dict objects
    """
    all_templates = list()

    try:
        db_templates = Template.query.filter(Template.type == 'init-cfg')
        for t in db_templates:
            db_template = dict()
            db_template['name'] = t.name
            db_template['description'] = t.description
            db_template['type'] = t.type
            all_templates.append(db_template)

    except SQLAlchemyError as sqe:
        print('Could not list init-cfg templates')
        print(sqe)
    finally:
        return all_templates


def get_template(template_name):
    """
    :param template_name: Name of the template to return
    :return: string containing the template content or None
    """
    try:
        t = Template.query.filter(Template.name == template_name).first()

        if t is None:
            print('Could not load template %s' % template_name)
            return None

        return t.template
    except SQLAlchemyError as sqe:
        print('Could not get template')
        print(sqe)
        return None


def get_required_vars_from_template(template_name):
    """
    Parse the template and return a list of all the variables defined therein
    template path is usually something like 'templates/panos/bootstrap.xml'
    :param template_name: relative path to the application root to a jinja2 template
    :return: set of variable named defined in the template
    """

    template_variables = set()

    try:
        t = Template.query.filter(Template.name == template_name).first()

        if t is None:
            print('Could not load template %s' % template_name)
            return template_variables

        # get the jinja environment to use it's parse function
        env = jinja2.Environment()
        # parse returns an AST that can be send to the meta module
        ast = env.parse(t.template)
        # return a set of all variable defined in the template
        template_variables = meta.find_undeclared_variables(ast)

    except TemplateSyntaxError as tse:
        print('Could not parse template')
        print(tse)
    except SQLAlchemyError as sqe:
        print('Could not load template variables')
        print(sqe)
    finally:
        return template_variables


def verify_data(template, available_vars):
    """
    Verify all the required variables have been posted from the user
    :param template: jinja2 template to check
    :param available_vars: dict of all available variables from the posted data and also the defaults
    :return:
    """
    vs = get_required_vars_from_template(template)
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

    init_cfg_vars = get_required_vars_from_template(init_cfg_name)
    for i in init_cfg_vars:
        available_variables.append(i)

    if bootstrap_name != "None" or bootstrap_name is not None:
        vs = get_required_vars_from_template(bootstrap_name)
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

    if 'bootstrap_template' in configuration_parameters:
        bootstrap_template_name = configuration_parameters['bootstrap_template']
    else:
        config = load_config()
        bootstrap_template_name = config.get('default_template', 'Default Bootstrap.xml')

    bootstrap_config = {}
    # populate with defaults if they exist
    if 'bootstrap' in defaults:
        bootstrap_config.update(defaults['bootstrap'])

    defined_vars = get_required_vars_from_template(bootstrap_template_name)
    # push all the required keys - should have already been validated
    for k in defined_vars:
        bootstrap_config[k] = configuration_parameters.get(k, None)

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

    print('Importing init-cfg-static')
    init_cfg_static = Template.query.filter(Template.name == 'init-cfg-static.txt').first()
    if init_cfg_static is None:
        print('Importing default init-cfg-static')
        ics_file_path = os.path.abspath(os.path.join(app.root_path, '..', 'templates/panos/init-cfg-static.txt'))
        try:
            print(
                'opening file init-cfg-static'
            )
            with open(ics_file_path, 'r') as icsf:
                i = Template(name='init-cfg-static.txt',
                             description='Init-Cfg with static management IP addresses',
                             template=icsf.read(),
                             type='init-cfg')

                print('add to db')
                db_session.add(i)
                print('commit to db')
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
                             description='Init-Cfg with DHCP Assigned IP addresses',
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
            print('this template does not exist %s' % it)
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


def build_base_configs(configuration_parameters):
    """
    Takes a dict of parameters and builds the base configurations
    :param configuration_parameters:  Simple dict of parameters
    :return: dict containing 'bootstrap.xml', 'authcodes', and 'init-cfg-static.txt' keys
    """

    config = load_config()
    defaults = load_defaults()
    print('WTF')
    # first check for a custom init-cfg file passed in as a parameter
    if 'init_cfg_template' in configuration_parameters:
        print('found a valid init_cfg_template')
        init_cfg_name = configuration_parameters['init_cfg_template']
        init_cfg_template = get_template(init_cfg_name)
        print(init_cfg_template)
        if init_cfg_template is None:
            init_cfg_template = get_template(config.get('default_init_cfg'), 'init-cfg-static.txt')
    else:
        print('using default init-cfg')
        init_cfg_name = config.get('default_init_cfg', 'init-cfg-static.txt')
        init_cfg_template = get_template(init_cfg_name)

    if init_cfg_template is None:
        print('init-cfg-template template was None')
        raise TemplateNotFoundError('Could not load %s' % init_cfg_name)

    print('getting required_keys')
    common_required_keys = get_required_vars_from_template(init_cfg_name)

    if not common_required_keys.issubset(configuration_parameters):
        print("Not all required keys are present for build_base_config!!")
        raise RequiredParametersError("Not all required keys are present for build_base_config!!")

    init_cfg_contents = render_template_string(init_cfg_template, **configuration_parameters)
    init_cfg_key = cache_utils.set(init_cfg_contents)

    base_config = dict()
    base_config['init-cfg.txt'] = dict()
    base_config['init-cfg.txt']['key'] = init_cfg_key
    base_config['init-cfg.txt']['archive_path'] = 'config'
    base_config['init-cfg.txt']['url'] = config["base_url"] + '/get/' + init_cfg_key

    if 'auth_key' in configuration_parameters:
        authcode = render_template('panos/authcodes', **configuration_parameters)
        authcode_key = cache_utils.set(authcode)
        base_config['authcodes'] = dict()
        base_config['authcodes']['key'] = authcode_key
        base_config['authcodes']['archive_path'] = 'license'
        base_config['authcodes']['url'] = config["base_url"] + '/get/' + init_cfg_key

    if 'bootstrap_template' in configuration_parameters and configuration_parameters['bootstrap_template'] != 'None':
        print('Using a bootstrap_template here')
        print(configuration_parameters['bootstrap_template'])
        bootstrap_template_name = configuration_parameters['bootstrap_template']
        print(bootstrap_template_name)
        bootstrap_config = generate_boostrap_config_with_defaults(defaults, configuration_parameters)

        bootstrap_template = get_template(bootstrap_template_name)
        if bootstrap_template is None:
            raise TemplateNotFoundError('Could not load bootstrap template!')

        print("checking bootstrap required_variables")
        if not verify_data(bootstrap_template, bootstrap_config):
            raise RequiredParametersError('Not all required keys for bootstrap.xml are present')

        bootstrap_xml = render_template_string(bootstrap_template, **bootstrap_config)
        bs_key = cache_utils.set(bootstrap_xml)

        base_config['bootstrap.xml'] = dict()
        base_config['bootstrap.xml']['key'] = bs_key
        base_config['bootstrap.xml']['archive_path'] = 'config'
        base_config['bootstrap.xml']['url'] = config["base_url"] + '/get/' + bs_key

    return base_config


def build_openstack_heat(base_config, posted_json, archive=False):
    defaults = load_defaults()

    if not openstack_utils.verify_data(posted_json):
        raise RequiredParametersError("Not all required keys for openstack are present")

    # create the openstack config object that will be used to populate the HEAT template
    openstack_config = openstack_utils.generate_config(defaults, posted_json)
    if archive:
        # the rendered heat template should reference local files that will be included in the archive
        openstack_config['init_cfg'] = 'init-cfg-static.txt'
        openstack_config['bootstrap_xml'] = 'bootstrap.xml'
        openstack_config['authcodes'] = 'authcodes'
    else:
        openstack_config['init_cfg'] = base_config['init-cfg-static.txt']['url']
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

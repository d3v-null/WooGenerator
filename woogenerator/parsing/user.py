"""
Containers and parsers for processing user data
"""
from __future__ import absolute_import

from collections import OrderedDict
from pprint import pformat

from ..coldata import ColDataUser
from ..contact_objects import (ContactAddress, ContactName, ContactPhones,
                               RoleGroup, SocialMediaFields)
from ..utils import DescriptorUtils, Registrar, SanitationUtils, SeqUtils
from ..utils.clock import TimeUtils
from .abstract import CsvParseBase, ImportObject, ObjList


class UsrObjList(ObjList):
    """
    A list of `ImportUser` objects
    """

    def __init__(self, objects=None, indexer=None):
        super(UsrObjList, self).__init__(objects, indexer=None)
        self._obj_list_type = 'User'

    report_cols = ColDataUser.get_report_cols()

    def get_sanitizer(self, tablefmt=None):
        if tablefmt == 'html':
            return SanitationUtils.sanitize_for_xml
        if tablefmt == 'simple':
            return SanitationUtils.sanitize_for_table
        return super(UsrObjList, self).get_sanitizer(tablefmt)

    @classmethod
    def get_basic_cols(cls, self):
        return ColDataUser.get_basic_cols()


class ImportUser(ImportObject):
    container = UsrObjList

    wpid = DescriptorUtils.safe_key_property('Wordpress ID')
    # TODO: does this break anything?
    email = DescriptorUtils.safe_normalized_key_property('E-mail')
    # email = DescriptorUtils.safe_key_property('E-mail')
    MYOBID = DescriptorUtils.safe_key_property('MYOB Card ID')
    username = DescriptorUtils.safe_key_property('Wordpress Username')
    role = DescriptorUtils.safe_key_property('Role Info')
    direct_brand = DescriptorUtils.safe_key_property('Direct Brand')
    # contact_schema = DescriptorUtils.safe_key_property('contact_schema')
    billing_address = DescriptorUtils.safe_key_property('Address')
    shipping_address = DescriptorUtils.safe_key_property('Home Address')
    name = DescriptorUtils.safe_key_property('Name')
    socials = DescriptorUtils.safe_key_property('Social Media')
    phones = DescriptorUtils.safe_key_property('Phone Numbers')

    alias_mapping = ColDataUser.get_alias_mapping()

    # alias_mapping = {
    #     'Address':[
    #         'Address 1', 'Address 2', 'City', 'Postcode', 'State', 'Country'
    #     ],
    #     'Home Address': [
    #         'Home Address 1', 'Home Address 2', 'Home City', 'Home Postcode',
    #         'Home State', 'Home Country'
    #     ],
    #     'Name': [
    #         'Name Prefix', 'First Name', 'Middle Name', 'Surname',
    #         'Name Suffix', 'Company', 'Memo', 'Contact'
    #     ],
    #     'Phone Numbers': ['Phone', 'Mobile Phone', 'Fax'],
    #     'Social Media': [
    #         'Facebook Username',
    #         'Twitter Username',
    #         'GooglePlus Username',
    #         'Instagram Username',
    #         'Web Site',
    #     ],
    #     'Role Info': [
    #         'Role',
    #         'Direct Brand'
    #     ],
    #     # 'E-mails': ['E-mail', 'Personal E-mail']
    # }

    @property
    def index(self):
        return " | ".join(SeqUtils.filter_unique_true([
            str(self.rowcount),
            str(self.wpid),
            str(self.MYOBID)
        ]))

    @property
    def act_modtime(self):
        time_str = self.get('Edited in Act')
        if time_str:
            return TimeUtils.act_strp_mktime(time_str)

    @property
    def act_created(self):
        time_str = self.get('Create Date')
        if time_str:
            return TimeUtils.act_strp_mktime(time_str)

    @property
    def wp_created(self):
        time_str = self.get('Wordpress Start Date')
        if time_str:
            return TimeUtils.wp_strp_mktime(time_str)

    @property
    def wp_modtime(self):
        time_str = self.get('Edited in Wordpress')
        if time_str and time_str != u'False':
            return TimeUtils.wp_server_to_local_time(
                TimeUtils.wp_strp_mktime(time_str))

    @property
    def last_sale(self):
        time_str = self.get('Last Sale')
        if time_str:
            return TimeUtils.act_strp_mkdate(time_str)

    @property
    def last_modtime(self):
        times = [
            self.act_modtime, self.wp_modtime, self.act_created,
            self.wp_created, self.last_sale
        ]
        return max(times)

    @property
    def act_last_transaction(self):
        """ effective last sale (if no last sale, use act create date) """
        response = self.last_sale
        if not response:
            response = self.act_created
        # assert response, "customer should always have a create (%s) or last sale (%s)" % (
        #     self.act_created, self.last_sale)
        return response

    def __init__(self, data, **kwargs):
        try:
            assert \
                isinstance(data, dict), \
                "expected data to be a dict, instead found: %s" % type(data)
        except AssertionError as exc:
            try:
                data = OrderedDict(data)
            except Exception:
                raise exc
        super(ImportUser, self).__init__(data, **kwargs)
        for key in [
                'E-mail', 'MYOB Card ID', 'Wordpress Username',  # 'Role',
                'contact_schema', 'Wordpress ID'
        ]:
            val = kwargs.get(key, "")
            if val:
                self[key] = val
            elif not self.get(key):
                self[key] = ""
            if self.DEBUG_USR:
                self.register_message(
                    "key: {key}, value: {val}".format(key=key, val=self[key]))
        if self.DEBUG_USR:
            self.register_message("data:" + repr(data))
        self.init_contact_objects(data)

    def init_contact_objects(self, data):
        # emails_kwargs = OrderedDict(filter(None, [\
        #     ((key, data.get(value)) if data.get(value) else None) for key, value in\
        #     {
        #         'email'         : 'E-mail',
        #         'personal_email': 'Personal E-mail',
        #     }.items()
        # ]))
        #
        # self['E-mails'] = EmailFields(
        #     **emails_kwargs
        # )

        schema = data.get('schema')
        # if self.DEBUG_MESSAGE:
        #     self.register_message("setting schema to %s" % schema)

        name_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None) for key, value in
            {
                'first_name': 'First Name',
                'middle_name': 'Middle Name',
                'family_name': 'Surname',
                'name_prefix': 'Name Prefix',
                'name_suffix': 'Name Suffix',
                'contact': 'Contact',
                'company': 'Company',
                # 'city': 'City',
                # 'country': 'Country',
                # 'state': 'State',
                'display_name': 'Display Name',
                'memo': 'Memo',
                'business_owner': 'Spouse',
                'saultation': 'Salutation'
            }.items()
        ]))

        self['Name'] = ContactName(schema, **name_kwargs)

        assert self['Name'] is not None, \
            'contact is missing mandatory fields: something went wrong'

        address_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None)
            for key, value in
            {
                'line1': 'Address 1',
                'line2': 'Address 2',
                'city': 'City',
                'postcode': 'Postcode',
                'state': 'State',
                'country': 'Country',
                'company': 'Company',
            }.items()
        ]))

        if self.DEBUG_ADDRESS:
            self.register_message("address_kwargs: %s" % address_kwargs)

        self['Address'] = ContactAddress(schema, **address_kwargs)

        alt_address_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None) for key, value in
            {
                'line1': 'Home Address 1',
                'line2': 'Home Address 2',
                'city': 'Home City',
                'postcode': 'Home Postcode',
                'state': 'Home State',
                'country': 'Home Country',
                'company': 'Company',
            }.items()
        ]))

        self['Home Address'] = ContactAddress(schema, **alt_address_kwargs)

        phone_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None) for key, value in
            {
                'mob_number': 'Mobile Phone',
                'tel_number': 'Phone',
                'fax_number': 'Fax',
                'pref_method': 'Pref Method',
                'source': 'source'
            }.items()
        ]))
        phone_kwargs['pref_data'] = ColDataUser.data.get('Pref Method', {})

        self['Phone Numbers'] = ContactPhones(schema, **phone_kwargs)

        social_media_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None) for key, value in
            {
                'facebook': 'Facebook Username',
                'twitter': 'Twitter Username',
                'gplus': 'GooglePlus Username',
                'instagram': 'Instagram Username',
                # 'website': 'Web Site',
            }.items()
        ]))

        urls = []
        if data.get('Web Site'):
            urls = SanitationUtils.find_all_urls(data['Web Site'])
            if not urls:
                urls = SanitationUtils.find_all_domains(data['Web Site'])
        social_media_kwargs['website'] = urls.pop(0) if urls else None

        if self.DEBUG_USR and self.DEBUG_CONTACT:
            self.register_message(
                "social_media_kwargs: %s" %
                pformat(social_media_kwargs))

        self['Social Media'] = SocialMediaFields(schema, **social_media_kwargs)

        if self.DEBUG_USR and self.DEBUG_CONTACT:
            self.register_message("Social Media: %s, type: %s, properties\n%s, kwargs\n%s" % (
                str(self['Social Media']),
                type(self['Social Media']),
                pformat(self['Social Media'].properties.items()),
                pformat(self['Social Media'].kwargs.items()),
            ))

        role_info_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None) for key, value in
            {
                'role': 'Role',
                'direct_brand': 'Direct Brand'
            }.items()
        ]))

        self['Role Info'] = RoleGroup(schema, **role_info_kwargs)

        if self.DEBUG_USR and self.DEBUG_CONTACT:
            self.register_message("Role Info: %s, type: %s, properties\n%s" % (
                str(self['Role Info']),
                type(self['Role Info']),
                pformat(self['Role Info'].properties.items())
            ))

        emails = []
        if data.get('E-mail'):
            emails = SeqUtils.combine_lists(
                emails, SanitationUtils.find_all_emails(data['E-mail']))
        if data.get('Personal E-mail'):
            emails = SeqUtils.combine_lists(
                emails,
                SanitationUtils.find_all_emails(data.get('Personal E-mail')))
        self['E-mail'] = emails.pop(0) if emails else None
        self['Personal E-mail'] = ', '.join(emails)

        # if not self['Emails'].valid:
        #     self['emails_reason'] = '\n'.join(filter(None, [
        #         self['Emails'].reason,
        #     ]))

        if not self['Address'].valid or not self['Home Address'].valid:
            self['address_reason'] = '\n'.join(
                filter(None, [
                    'ADDRESS: ' + self['Address'].reason if not self['Address']
                    .valid else None, 'HOME ADDRESS: ' + self['Home Address']
                    .reason if not self['Home Address'].valid else None
                ]))

        if not self['Name'].valid:
            self['name_reason'] = '\n'.join(
                filter(None, [
                    self['Name'].reason,
                ]))

        if not self['Phone Numbers'].valid:
            self['phone_reason'] = '\n'.join(
                filter(None, [
                    self['Phone Numbers'].reason,
                ]))

        if not self['Social Media'].valid:
            self['social_reason'] = '\n'.join(
                filter(None, [
                    self['Social Media'].reason,
                ]))

    def refresh_contact_objects(self):
        pass
        # self.init_contact_objects(self.__getstate__())

    def __getitem__(self, key):
        # if self.DEBUG_MESSAGE:
        #     self.register_message("getting %s in %s" % (
        #         key,
        #         id(self),
        #     ))
        for alias, keys in self.alias_mapping.items():
            if key in keys and alias in self and self[alias] is not None:
                return self[alias][key]
        return super(ImportUser, self).__getitem__(key)

    def __setitem__(self, key, val):
        # print "setting obj %s to %s " % (key, repr(val))
        # if self.DEBUG_MESSAGE:
        #     self.register_message("setting %s in %s to %s" % (
        #         key,
        #         id(self),
        #         repr(val)
        #     ))
        if key == 'Role Info' and val == '':
            raise Exception()
        for alias, keys in self.alias_mapping.items():
            if key in keys and alias in self:
                self[alias][key] = val
                return
        super(ImportUser, self).__setitem__(key, val)
        # if key is 'Name':

    # print self.__getitem__(key)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    @staticmethod
    def get_new_obj_container():
        return UsrObjList

    def addresses_act_like(self):
        act_like = True
        for address in [
                self.get(key) for key in ['Address', 'Home Address']
        ]:
            if address and address.schema and address.schema != 'act':
                act_like = False
        return act_like

    def username_act_like(self):
        return self.username == self.MYOBID

    def __repr__(self):
        return "<%s> %s" % (
            self.index,
            " | ".join(map(str, [
                self.email,
                self.role,
                self.username,
            ]))
        )


class CsvParseUser(CsvParseBase):

    objectContainer = ImportUser

    def __init__(self,
                 cols=None,
                 defaults=None,
                 contact_schema=None,
                 filter_items=None,
                 limit=None,
                 source=None,
                 schema=None):
        if self.DEBUG_MRO:
            self.register_message(' ')
        self.schema = schema
        extra_cols = [
            # 'ABN', 'Added to mailing list', 'Address 1', 'Address 2', 'Agent', 'Birth Date',
            # 'book_spray_tan', 'Book-a-Tan Expiry', 'Business Type', 'Canvasser', ''
            # 'post_status'
        ]
        extra_defaults = OrderedDict([
            # ('post_status', 'publish'),
            # ('last_import', import_name),
        ])
        cols = SeqUtils.combine_lists(cols, extra_cols)
        defaults = SeqUtils.combine_ordered_dicts(defaults, extra_defaults)
        super(CsvParseUser, self).__init__(
            cols, defaults, limit=limit, source=source)
        self.contact_schema = contact_schema
        self.filter_items = filter_items

    def clear_transients(self):
        if self.DEBUG_MRO:
            self.register_message(' ')
        super(CsvParseUser, self).clear_transients()
        self.roles = OrderedDict()
        self.noroles = OrderedDict()
        self.emails = OrderedDict()
        self.noemails = OrderedDict()
        self.cards = OrderedDict()
        self.nocards = OrderedDict()
        self.usernames = OrderedDict()
        self.nousernames = OrderedDict()
        # self.companies = OrderedDict()
        self.addresses = OrderedDict()
        self.filtered = OrderedDict()
        self.bad_name = OrderedDict()
        self.bad_address = OrderedDict()
        # self.badEmail = OrderedDict()

    def sanitize_cell(self, cell):
        return SanitationUtils.sanitize_cell(cell)

    def register_email(self, object_data, email):
        # TODO: does this line break anything?
        email = SanitationUtils.normalize_val(email)
        self.register_anything(
            object_data,
            self.emails,
            email,
            singular=False,
            register_name='emails')

    def register_no_email(self, object_data):
        self.register_anything(
            object_data,
            self.noemails,
            object_data.index,
            singular=True,
            register_name='noemails')

    def register_role(self, object_data, role):
        self.register_anything(
            object_data, self.roles, role, singular=False, register_name='roles')

    def register_no_role(self, object_data):
        self.register_anything(
            object_data,
            self.noroles,
            object_data.index,
            singular=True,
            register_name='noroles')

    def register_card(self, object_data, card):
        self.register_anything(
            object_data, self.cards, card, singular=False, register_name='cards')

    def register_no_card(self, object_data):
        self.register_anything(
            object_data,
            self.nocards,
            object_data.index,
            singular=True,
            register_name='nocards')

    def register_username(self, object_data, username):
        self.register_anything(
            object_data,
            self.usernames,
            username,
            singular=False,
            register_name='usernames')

    def register_no_username(self, object_data):
        self.register_anything(
            object_data,
            self.nousernames,
            object_data.index,
            singular=True,
            register_name='nousernames')

    # def registerCompany(self, object_data, company):
    #     self.register_anything(
    #         object_data,
    #         self.companies,
    #         company,
    #         singular = False,
    #         register_name = 'companies'
    #     )

    def register_filtered(self, object_data, reason):
        self.register_anything(
            (object_data, reason),
            self.filtered,
            object_data.index,
            singular=True,
            register_name='filtered')

    def register_bad_address(self, object_data, _):
        self.register_anything(
            object_data,
            self.bad_address,
            object_data.index,
            singular=True,
            register_name='badaddress')

    def register_bad_name(self, object_data, _):
        self.register_anything(
            object_data,
            self.bad_name,
            object_data.index,
            singular=True,
            register_name='badname')

    # def registerBadEmail(self, object_data, name):
    #     self.register_anything(
    #         object_data,
    #         self.badEmail,
    #         object_data.index,
    #         singular = True,
    #         register_name = 'bademail'
    #     )

    def register_address(self, object_data, address):
        address_str = str(address)
        if address_str:
            self.register_anything(
                object_data,
                self.addresses,
                address_str,
                singular=False,
                register_name='address')

    def validate_filters(self, object_data):
        if self.filter_items:
            if 'roles' in self.filter_items \
                    and SanitationUtils.normalize_val(object_data.role) \
                    not in self.filter_items['roles']:
                return "did not match role conditions"
            if self.source == self.master_name \
                    and 'since_m' in self.filter_items \
                    and object_data.act_modtime < self.filter_items['since_m']:
                return "did not meet since_m condition"
            if self.source == self.slave_name \
                    and 'since_s' in self.filter_items \
                    and object_data.wp_modtime < self.filter_items['since_s']:
                return "did not meet since_s condition"
            if 'users' in self.filter_items \
                    and SanitationUtils.normalize_val(object_data.username) \
                    not in self.filter_items['users']:
                return "did not meet username condition"
            if 'cards' in self.filter_items \
                    and SanitationUtils.normalize_val(object_data.MYOBID) \
                    not in self.filter_items['cards']:
                return "did not meet cards condition"
            if 'ignore_cards' in self.filter_items \
                    and SanitationUtils.normalize_val(object_data.MYOBID) \
                    in self.filter_items['ignore_cards']:
                return "did not meet ignore cards condition"
            if 'emails' in self.filter_items \
                    and SanitationUtils.normalize_val(object_data.email) \
                    not in self.filter_items['emails']:
                return "did not meet emails condition"

    def register_object(self, object_data):
        reason = self.validate_filters(object_data)
        if reason:
            if self.DEBUG_USR:
                self.register_message(
                    "could not register object %s because %s" % (
                        object_data.__repr__(), reason
                    ))
            self.register_filtered(object_data, reason)
            return

        email = object_data.email
        if email and SanitationUtils.string_is_email(email):
            self.register_email(object_data, email)
        else:
            if self.DEBUG_USR:
                self.register_warning("invalid email address: %s" % email)
            self.register_no_email(object_data)

        role = object_data.role.role
        if role:
            self.register_role(object_data, role)
        else:
            # self.register_warning("invalid role: %s"%role)
            self.register_no_role(object_data)

        card = object_data.MYOBID
        if card and SanitationUtils.string_is_myobid(card):
            self.register_card(object_data, card)
        else:
            self.register_no_card(object_data)

        username = object_data.username
        if username:
            self.register_username(object_data, username)
        else:
            if self.DEBUG_USR:
                self.register_warning("invalid username: %s" % username)
            self.register_no_username(object_data)

        # company = object_data['Company']
        # # if self.DEBUG_USR: SanitationUtils.safe_print(repr(object_data), company)
        # if company:
        #     self.registerCompany(object_data, company)

        addresses = [object_data.billing_address, object_data.shipping_address]
        for address in filter(None, addresses):
            if not address.valid:
                reason = address.reason
                assert reason, "there must be a reason that this address is invalid: " + address
                self.register_bad_address(object_data, address)
            else:
                self.register_address(object_data, address)

        name = object_data.name
        # print "NAME OF %s IS %s" % (repr(object_data),
        # name.__str__(out_schema="flat"))
        if not name.valid:
            reason = name.reason
            assert reason, "there must be a reason that this name is invalid: " + name
            # print "registering bad name: ",
            # SanitationUtils.coerce_bytes(name)
            self.register_bad_name(object_data, name)

        # emails = object_data.emails
        # if not emails.valid:
        #     reason = emails.reason
        #     self.registerBadEmail(object_data, emails)

        super(CsvParseUser, self).register_object(object_data)

    def get_parser_data(self, **kwargs):
        data = super(CsvParseUser, self).get_parser_data(**kwargs)
        if 'contact_schema' not in data:
            data['contact_schema'] = self.contact_schema
        if 'schema' not in data:
            data['schema'] = self.schema
        return data

    # def get_kwargs(self, all_data, container, **kwargs):
    #     kwargs = super(CsvParseUser, self).get_kwargs(
    #         all_data, container, **kwargs
    #     )
    #     return kwargs

    # def processRoles(self, object_data):
    #     role = object_data.role
    #     if not self.roles.get(role): self.roles[role] = OrderedDict()
    #     self.register_anything(
    #         object_data,
    #         self.roles[role],
    #         self.getUsername,
    #         singular = True,
    #         register_name = 'roles'
    #     )

    # def process_object(self, object_data):
    #     # object_data.username = self.getMYOBID(object_data)
    #     super(CsvParseFlat, self).process_object(object_data)
    #     self.processRoles(object_data)

    # def analyzeRow(self, row, object_data):
    #     object_data = super(CsvParseFlat, self).analyseRow(row, object_data)
    #     return object_data


class CsvParseUserApi(CsvParseUser):

    @classmethod
    def get_parser_data(cls, **kwargs):
        """
        Gets data ready for the parser, in this case from api_data
        """
        parser_data = OrderedDict()
        api_data = kwargs.get('api_data', {})
        # print "api_data before: %s" % str(api_data)
        api_data = dict([(key, SanitationUtils.html_unescape_recursive(value))
                         for key, value in api_data.items()])
        # print "api_data after:  %s" % str(api_data)
        parser_data = OrderedDict()
        core_translation = OrderedDict()
        for col, col_data in ColDataUser.get_wpapi_core_cols().items():
            try:
                wp_api_key = col_data['wp-api']['key']
            except BaseException:
                wp_api_key = col
            core_translation[wp_api_key] = col
        if Registrar.DEBUG_API:
            Registrar.register_message("core_translation: %s" %
                                       pformat(core_translation))
        parser_data.update(**cls.translate_keys(api_data, core_translation))

        if 'meta' in api_data:
            meta_translation = OrderedDict()
            meta_data = api_data['meta']
            # if Registrar.DEBUG_API:
            #     Registrar.register_message(
            #         "meta data: %s" % pformat(
            #             ColDataUser.get_wpapi_meta_cols().items()
            #         )
            #     )
            for col, col_data in ColDataUser.get_wpapi_meta_cols().items():
                try:
                    if 'wp-api' in col_data:
                        wp_api_key = col_data['wp-api']['key']
                    elif 'wp' in col_data:
                        wp_api_key = col_data['wp']['key']
                except Exception:
                    wp_api_key = col

                meta_translation[wp_api_key] = col
            if Registrar.DEBUG_API:
                Registrar.register_message("meta_translation: %s" %
                                           pformat(meta_translation))
            meta_translation_result = cls.translate_keys(meta_data,
                                                         meta_translation)
            # if Registrar.DEBUG_API:
            #     Registrar.register_message(
            #         "meta_translation_result: %s" % pformat(meta_translation_result)
            #     )
            parser_data.update(**meta_translation_result)

        if Registrar.DEBUG_API:
            Registrar.register_message(
                "parser_data: {}".format(pformat(parser_data)))
        return parser_data

    def analyse_wp_api_obj(self, api_data):
        kwargs = {'api_data': api_data}
        object_data = self.new_object(rowcount=self.rowcount, **kwargs)
        if self.DEBUG_API:
            self.register_message("CONSTRUCTED: %s" % object_data.identifier)
        self.process_object(object_data)
        if self.DEBUG_API:
            self.register_message("PROCESSED: %s" % object_data.identifier)
        self.register_object(object_data)
        if self.DEBUG_API:
            self.register_message("REGISTERED: %s" % object_data.identifier)
        # self.register_message("mro: {}".format(container.mro()))
        self.rowcount += 1

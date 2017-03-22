
from woogenerator.utils import DescriptorUtils, SeqUtils, SanitationUtils, TimeUtils
from woogenerator.parsing.abstract import CsvParseBase, ImportObject, ObjList

USRS_PER_FILE = 1000


class ImportFlat(ImportObject):
    pass


class CsvParseFlat(CsvParseBase):
    objectContainer = ImportFlat
    # def __init__(self, cols, defaults):
    #     super(CsvParseFlat, self).__init__(cols, defaults)


class ImportSpecial(ImportFlat):

    ID = DescriptorUtils.safe_key_property('ID')
    start_time = DescriptorUtils.safe_key_property('start_time')
    end_time = DescriptorUtils.safe_key_property('end_time')

    # @property
    # def start_time_iso(self): return TimeUtils.isoTimeToString(self.start_time)

    # @property
    # def end_time_iso(self): return TimeUtils.isoTimeToString(self.end_time)

    def __init__(self, data, **kwargs):
        if self.DEBUG_MRO:
            self.register_message(' ')
        for key in ["FROM", "TO"]:
            if key not in data:
                raise UserWarning(
                    "Missing %s field. data: %s, kwargs: %s" % (key, data, kwargs))
        super(ImportSpecial, self).__init__(data, **kwargs)
        try:
            self.ID
        except:
            raise UserWarning('ID exist for Special to be valid')

        self['start_time'] = TimeUtils.g_drive_strp_mk_time(self['FROM'])
        self['end_time'] = TimeUtils.g_drive_strp_mk_time(self['TO'])

    @property
    def index(self):
        return self.ID

    def get_index(self):
        exc = DeprecationWarning("use .index instead of .get_index()")
        self.register_error(exc)
        return self.index


class CsvParseSpecial(CsvParseFlat):

    objectContainer = ImportSpecial

    def __init__(self, cols=None, defaults=None):
        if self.DEBUG_MRO:
            self.register_message(' ')
        if cols is None:
            cols = []
        if defaults is None:
            defaults = {}
        extra_cols = [
            "ID",
            "FROM",
            "TO",
            "RNS",
            "RPS",
            "WNS",
            "WPS",
            "XRNS",
            "XRPS",
            "XWNS",
            "XWPS"
        ]
        cols = SeqUtils.combine_lists(cols, extra_cols)

        super(CsvParseSpecial, self).__init__(cols, defaults)
        self.object_indexer = self.get_object_id

    @classmethod
    def get_object_id(self, object_data):
        return object_data.ID


class ImportSqlProduct(ImportFlat):
    ID = DescriptorUtils.safe_key_property('ID')
    codesum = DescriptorUtils.safe_key_property('codesum')
    itemsum = DescriptorUtils.safe_key_property('itemsum')

    @property
    def index(self):
        return self.codesum


class CsvParseWpSqlProd(CsvParseFlat):

    objectContainer = ImportSqlProduct

    """docstring for CsvParseWpSqlProd"""
    # def __init__(self, arg):
    # super(CsvParseWpSqlProd, self).__init__()

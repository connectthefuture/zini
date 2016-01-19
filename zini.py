from collections.abc import MutableMapping
from collections import namedtuple

__version__ = '0.0.1'

NOT_SET = type('NOT_SET', (), {})

V = namedtuple('V', ('type', 'default'))


class ParseError(Exception):
    def __init__(self, n, line):
        super().__init__(n, line)
        self.n = n
        self.line = line

    def __str__(self):  # pragma: no cover
        return "error in line {}: {!r}".format(self.n, self.line)


class Zini(MutableMapping):
    _file_name = None
    _content = None
    _result = None

    def __init__(self, **sections):
        self._sections = {}

        for name, data in sections.items():
            self[name] = data

    def __getitem__(self, key):
        section = self._sections.get(key)
        if section is None:
            self[key] = section = Section()

        return section

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("only strings is allowed for sectors name")
        elif isinstance(value, Section):
            self._sections[key] = value
        elif not isinstance(value, dict):
            raise TypeError("only dict or Sector is allowed for sectors")
        else:
            self[key] = Section(value)

    def __delitem__(self, key):
        del self._sections[key]

    def __iter__(self):  # pragma: no cover
        return iter(self._sections)

    def __len__(self):
        return len(self._sections)

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            repr(self._sections),
        )

    @property
    def file_name(self):
        return self._file_name

    @property
    def content(self):
        return self._content

    @property
    def result(self):
        return self._result

    def read(self, file_name):
        if self.file_name is not None:
            raise ValueError("other file is already readed: {!r}"
                             "".format(self.file_name))
        else:
            self._file_name = file_name

        with open(file_name) as f:
            content = f.read()

        return self.parse(content)

    def parse(self, content):
        if self.content is not None:
            raise ValueError("already parsed")
        else:
            content = content
            self._content = content

        result = {}

        section = None

        for n, line in enumerate(content.split('\n')):
            line = line.rstrip()

            if not line:
                # skip empty
                continue
            elif line[0] in '#;':
                # skip comments
                continue
            elif line.startswith(' '):
                # indentation not allowed for future b/c
                raise ParseError(n, line)
            elif line.startswith('[') and line.endswith(']'):
                # setup section
                section = line[1:-1]
            elif '=' not in line:
                # must be keyvalue
                raise ParseError(n, line)
            elif section is None:
                # first keyvalue is not sector
                raise ParseError(n, line)
            else:
                key, value = self[section]._parse_keyvalue(n, line)
                result.setdefault(section, {})[key] = value

        for name, sector in self.items():
            # set defaults
            for key, v in sector.items():
                if v.default is not NOT_SET:
                    result[name].setdefault(key, v.default)

        self._result = result
        return result


class Section(MutableMapping):
    def __init__(self, data=None):
        self._data = {}
        if data is not None:
            for k, v in data.items():
                self[k] = v

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("only strings is allowed for keys")
        elif isinstance(value, type):
            v = V(value, NOT_SET)
        else:
            v = V(type(value), value)

        self._check_type(v.type)

        self._data[key] = v

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):  # pragma: no cover
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            repr(self._data),
        )

    def _check_type(self, t):
        if t not in [str, int, float, bool]:
            raise TypeError("unknown type: {t.__name__}".format(t=t))

    def _parse_keyvalue(self, n, line):
        key, value = (i.strip() for i in line.split('=', 1))
        if not key or not value:
            raise ParseError(n, line)

        parsers = [self._get_bool, int, float, self._get_str]

        for func in parsers:
            try:
                value = func(value)
                break
            except ValueError:
                pass
        else:
            raise ParseError(n, line)

        if key in self and not isinstance(value, self[key].type):
            raise ParseError(n, line)
        else:
            return key, value

    @staticmethod
    def _get_bool(value):
        if value.lower() == 'false':
            return False
        elif value.lower() == 'true':
            return True
        else:
            raise ValueError

    @staticmethod
    def _get_str(value):
        if len(value) < 2:
            raise ValueError
        elif ((value[0] == '"' and value[-1] == '"') or
                (value[0] == "'" and value[-1] == "'")):
            return value[1:-1]
        else:
            raise ValueError

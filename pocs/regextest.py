if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import re
from source.utils import SanitationUtils

# can negative lookahead work on a group?

print re.match(r"(?!.*a.*| .*)(\w+)", "bab")

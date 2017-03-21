# -*- coding: utf-8 -*-
from utils import SanitationUtils
from kitchen.text import converters


def printandrep(name, thing, back=""):
    fmt_str = "%32s |"
    print fmt_str % name, fmt_str % converters.to_bytes(thing), fmt_str % repr(thing), fmt_str % converters.to_bytes(back), fmt_str % converters.to_bytes(unicode(back))

u_str = u"<\U0001F44C'&>"
utf8_str = SanitationUtils.unicode_to_utf8(u_str)
utf8_back = SanitationUtils.utf8_to_unicode(utf8_str)
xml_str = SanitationUtils.unicode_to_xml(u_str)
xml_back = SanitationUtils.xml_to_unicode(xml_str)
ascii_str = SanitationUtils.unicode_to_ascii(u_str)
ascii_back = SanitationUtils.ascii_to_unicode(u_str)

printandrep("u_str", u_str)
printandrep("utf8_str", utf8_str, utf8_back)
printandrep("xml_str", xml_str, xml_back)
printandrep("ascii_str", ascii_str, ascii_back)

print SanitationUtils.unicode_to_utf8(None)
print SanitationUtils.utf8_to_unicode(None)
print SanitationUtils.unicode_to_xml(None)
print SanitationUtils.xml_to_unicode(None)
print SanitationUtils.unicode_to_ascii(None)
print SanitationUtils.ascii_to_unicode(None)
print SanitationUtils.coerce_unicode(None)
SanitationUtils.safe_print(None)

print converters.to_bytes(SanitationUtils.coerce_unicode("\xf0\x9f\x91\x8c"))

print converters.to_bytes(SanitationUtils.unicode_to_xml("\xf0\x9f\x91\x8c".decode("utf8"), True))
print converters.xml_to_unicode("&#76;")
print converters.xml_to_byte_string("&#76;")
print converters.to_bytes(converters.xml_to_unicode("&#12392;"))
print converters.to_bytes(converters.xml_to_byte_string("&#12392;", input_encoding="ascii"))
print converters.xml_to_unicode("&#128076;", encoding="ascii")
print converters.xml_to_byte_string("&#128076;", input_encoding="ascii")


map_json = '{"E-mail":"neil@technotan.com.au","Web Site":"http:\/\/technotan.com.au","MYOB Customer Card ID":[""],"MYOB Card ID":[""],"First Name":["Neil \ud83d\udc4c\'&amp;&gt;"],"Surname":["Cunliffe-Williams"],"Contact":["Neil Cunliffe-Williams"],"Company":["Laserphile"],"Address 1":["7 Grosvenor Road"],"Address 2":[""],"City":[""],"Postcode":["6053"],"State":["WA"],"Phone":["0416160912"],"Home Address 1":["7 Grosvenor Road"],"Home Address 2":[""],"Home City":["Bayswater"],"Home Postcode":["6053"],"Home Country":["AU"],"Home State":["WA"],"Role":["ADMIN"],"ABN":["32"],"Business Type":[""],"Birth Date":[""],"Mobile Phone":["+61416160912"],"Fax":[""],"Lead Source":[""],"Referred By":[""]}'

# unicode_to_utf8(u_str)
# unicode_to_ascii(u_str)
# unicode_to_xml(u_str)
# utf8_to_unicode(utf8_str)
# xml_to_unicode(utf8_str)
# ascii_to_unicode(ascii_str)
# coerce_unicode(thing)
# coerce_bytes(thing)

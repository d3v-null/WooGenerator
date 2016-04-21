# -*- coding: utf-8 -*-
from utils import SanitationUtils
from kitchen.text import converters

def printandrep(name, thing, back = ""):
    fmt_str = "%32s |"
    print fmt_str % name, fmt_str % converters.to_bytes(thing), fmt_str % repr(thing), fmt_str % converters.to_bytes(back), fmt_str % converters.to_bytes(unicode(back))

u_str = u"<\U0001F44C'&>"
utf8_str = SanitationUtils.unicodeToUTF8(u_str)
utf8_back = SanitationUtils.utf8ToUnicode(utf8_str)
xml_str = SanitationUtils.unicodeToXml(u_str)
xml_back = SanitationUtils.xmlToUnicode(xml_str)
ascii_str = SanitationUtils.unicodeToAscii(u_str)
ascii_back = SanitationUtils.asciiToUnicode(u_str)

printandrep( "u_str", u_str )
printandrep( "utf8_str", utf8_str, utf8_back )
printandrep( "xml_str", xml_str, xml_back )
printandrep( "ascii_str", ascii_str, ascii_back )

print SanitationUtils.unicodeToUTF8(None)
print SanitationUtils.utf8ToUnicode(None)
print SanitationUtils.unicodeToXml(None)
print SanitationUtils.xmlToUnicode(None)
print SanitationUtils.unicodeToAscii(None)
print SanitationUtils.asciiToUnicode(None)
print SanitationUtils.coerceUnicode(None)
SanitationUtils.safePrint(None)

print converters.to_bytes(SanitationUtils.coerceUnicode("\xf0\x9f\x91\x8c"))

print converters.to_bytes(SanitationUtils.unicodeToXml("\xf0\x9f\x91\x8c".decode("utf8"), True))
print converters.xml_to_unicode("&#76;")
print converters.xml_to_byte_string("&#76;")
print converters.to_bytes(converters.xml_to_unicode("&#12392;"))
print converters.to_bytes(converters.xml_to_byte_string("&#12392;", input_encoding="ascii"))
print converters.xml_to_unicode("&#128076;", encoding="ascii")
print converters.xml_to_byte_string("&#128076;", input_encoding="ascii")


map_json = '{"E-mail":"neil@technotan.com.au","Web Site":"http:\/\/technotan.com.au","MYOB Customer Card ID":[""],"MYOB Card ID":[""],"First Name":["Neil \ud83d\udc4c\'&amp;&gt;"],"Surname":["Cunliffe-Williams"],"Contact":["Neil Cunliffe-Williams"],"Company":["Laserphile"],"Address 1":["7 Grosvenor Road"],"Address 2":[""],"City":[""],"Postcode":["6053"],"State":["WA"],"Phone":["0416160912"],"Home Address 1":["7 Grosvenor Road"],"Home Address 2":[""],"Home City":["Bayswater"],"Home Postcode":["6053"],"Home Country":["AU"],"Home State":["WA"],"Role":["ADMIN"],"ABN":["32"],"Business Type":[""],"Birth Date":[""],"Mobile Phone":["+61416160912"],"Fax":[""],"Lead Source":[""],"Referred By":[""]}'

    # unicodeToUTF8(u_str)
    # unicodeToAscii(u_str)
    # unicodeToXml(u_str)
    # utf8ToUnicode(utf8_str)
    # xmlToUnicode(utf8_str)
    # asciiToUnicode(ascii_str)
    # coerceUnicode(thing)
    # coerceBytes(thing)
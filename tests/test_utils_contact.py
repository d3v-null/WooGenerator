def test_name_utils():
    pass
    # print SanitationUtils.compile_abbrv_regex(NameUtils.noteAbbreviations)
    # print NameUtils.tokenize_name('DERWENT (ACCT)')
    # print NameUtils.get_email('KYLIESWEET@GMAIL.COM')

    # assert r'\'' in SanitationUtils.allowedPunctuation
    # assert r'\'' not in SanitationUtils.disallowedPunctuation
    # assert r'\'' not in SanitationUtils.tokenDelimeters
    #
    # print SanitationUtils.tokenDelimeters
    #
    # match = re.match(
    #     '(' + SanitationUtils.nondelimeterRegex + ')',
    #     '\''
    # )
    # if match: print "nondelimeterRegex", [match_item for match_item in match.groups()]
    #
    # match = re.match(
    #     '(' + SanitationUtils.delimeterRegex + ')',
    #     '\''
    # )
    # if match: print "delimeterRegex", [match_item for match_item in match.groups()]
    #
    # match = re.match(
    #     NameUtils.singleNameRegex,
    #     'OCAL\'LAGHAN'
    # )
    # if match: print [match_item for match_item in match.groups()]

    # print "singlename", repr( NameUtils.get_single_name('O\'CALLAGHAN' ))
    # def testNotes(line):
    #     for token in NameUtils.tokenize_name(line):
    #         print token, NameUtils.get_note(token)
    #
    # testNotes("DE-RWENT- FINALIST")
    # testNotes("JAGGERS HAIR- DO NOT WANT TO BE CALLED!!!!")


    # def testAddressUtils():
    #     # SanitationUtils.clearStartRegex = "<START>"
    #     # SanitationUtils.clearFinishRegex = "<FINISH>"
    #     # print repr(AddressUtils.addressTokenRegex)
    #
    #     # print AddressUtils.address_remove_end_word("WEST AUSTRALIA", "WEST AUSTRALIA")
    #
    #     # print AddressUtils.address_remove_end_word(
    #           "SHOP 7 KENWICK SHOPNG CNTR BELMONT RD, KENWICK WA (",
    #           "KENWICK WA"
    #     # )
    #     # print SanitationUtils.unicodeToByte(u"\u00FC ASD")
    #     # print "addressTokenRegex", AddressUtils.addressTokenRegex
    #     # print "thoroughfareRegex", AddressUtils.thoroughfareRegex
    #     # print "subunitRegex", AddressUtils.subunitRegex
    #     # print "floorLevelRegex", AddressUtils.floorLevelRegex
    #     # print "stateRegex", AddressUtils.stateRegex
    #     # print "delimeterRegex", AddressUtils.delimeterRegex
    #
    #     # print AddressUtils.get_subunit("SHOP 4 A")
    #     # print AddressUtils.get_floor("LEVEL 8")
    #     print AddressUtils.tokenize_address("BROADWAY FAIR SHOPPING CTR")
    #     print AddressUtils.get_building("BROADWAY FAIR SHOPPING CTR")
    #     print AddressUtils.get_building("BROADWAY FAIR SHOPPING")
    #     print NameUtils.get_multi_name("BROADWAY")
    #

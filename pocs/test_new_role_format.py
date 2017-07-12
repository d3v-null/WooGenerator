from new_role_format import jess_fix
import unittest
from unittest import TestCase

#pylint: disable=C0330,C0301

class TestJessFix(TestCase):
    def test_jess_fix(self):
        for direct_brands, role, expected_brand, expected_role in [
            # If Direct Brand is TechnoTan and Role is WN - Change Direct Brand to TechnoTan Wholesale and keep Role as WN
            ("TechnoTan", "WN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand is TechnoTan and Role is RN - Change Direct Brand to TechnoTan Retail and keep Role as RN
            ("TechnoTan", "RN", "TechnoTan Retail", 'RN'),
            # If Direct Brand is VuTan and Role is WN - Change Direct Brand to VuTan Wholesale and keep Role as WN
            ("VuTan", "WN", "VuTan Wholesale", "WN"),
            # If Direct Brand is VuTan and Role is RN - Change Direct Brand to VuTan Retail and keep Role as RN
            ("VuTan", "RN", "VuTan Retail", "RN"),
            # If Direct Brand is TechnoTan Wholesale and Role is WP - Change Direct Brand to TechnoTan Wholesale Preferred and keep Role as WP
            ("TechnoTan Wholesale", "WP", "TechnoTan Wholesale Preferred", "WP"),
            # If Direct Brand is TechnoTan and Role is WP - Change Direct Brand to TechnoTan Wholesale Preferred and keep Role as WP
            ("TechnoTan", "WP", "TechnoTan Wholesale Preferred", "WP"),
            # If Direct Brand is VuTan Wholesale and Role is WP - Change Direct Brand to VuTan Wholesale Preferred and keep Role as WP
            ("VuTan Wholesale", "WP", "VuTan Wholesale Preferred", "WP"),
            # If Direct Brand is VuTan and Role is WP - Change Direct Brand to VuTan Wholesale Preferred and keep Role as WP
            ("VuTan", "WP", "VuTan Wholesale Preferred", "WP"),
            # If Direct Brand is TechnoTan Wholesale and Role is WN - Leave as is
            ("TechnoTan Wholesale", "WN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand is VuTan Wholesale and Role is WN - Leave as is
            ("VuTan Wholesale", "WN", "VuTan Wholesale", "WN"),
            # If Direct Brand is Pending and Role is WN - Leave Direct Brand as pending and change Role to RN
            ("Pending", "WN", "Pending", "RN"),
            # If Direct Brand is TechnoTan Wholesale and Role is WP - Change Direct Brand to TechnoTan Wholesale Preferred and keep Role as WP
                # Duplicate
            # If Direct Brand is VuTan Wholesale and Role is WP - Change Direct Brand to VuTan Wholesale Preferred and keep Role as WP
                # Duplicate
            # If Direct Brand is Tanbience and Role is WN - Change Direct Brand to Tanbience Retail and Role to RN
            ("Tanbience", "WN", "Tanbience", "RN"),
            # If Direct Brand is TechnoTan Wholesale and Role is RN - Change Role to WN
            ("TechnoTan Wholesale", "RN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand is VuTan Wholesale and Role is RN - Change Role to WN
            ("VuTan Wholesale", "RN", "VuTan Wholesale", "WN"),
            # If Direct Brand is PrintWorx and Role is WN - Change Role to RN
            ("PrintWorx", "WN", "PrintWorx", "RN"),
            # If customer has more than one direct brand that includes TechnoTan/TechnoTan Wholesale and role is set to WN - Keep role as WN
                # "???",
            # If customer has more than one direct brand that includes VuTan/VuTan Wholesale and role is set to WN - Keep role as WN
            # If Direct Brand is TechnoTan and Role is XWN - Change Direct Brand to TechnoTan Export and keep Role as XWN
            ("TechnoTan", "XWN", "TechnoTan Export Wholesale", "XWN"),
            # If Direct Brand is VuTan and Role is XWN - Change Direct Brand to VuTan Export and keep Role as XWN
            ("VuTan", "XWN", "VuTan Export Wholesale", "XWN"),
            # If Direct Brand is VuTan Distributor and Role is RN, WP or WN - Leave Direct Brand as is and change Role to DN
            ("VuTan Distributor", "RN", "VuTan Distributor", "DN"),
            ("VuTan Distributor", "WN", "VuTan Distributor", "DN"),
            ("VuTan Distributor", "WP", "VuTan Distributor", "DN"),
            # If Direct Brand is TechnoTan Retail and Role is WN - Change Direct Brand to TechnoTan Wholesale and leave Role as is
            ("TechnoTan Retail", "WN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand is VuTan Retail and Role is WN - Change Direct Brand to VuTan Wholesale and leave Role as is
            ("VuTan Retail", "WN", "VuTan Wholesale", "WN"),
            # If Direct Brand is Pending and Role is ADMIN - Change Direct Brand to Staff and leave Role as is (anyone with ADMIN as the role are staff members that need to have access to the back end of the website, so I'm not sure if Direct Brand Should be something else so all prices are visible?).
            ("Pending", "ADMIN", "Staff", "ADMIN"),
            # If Direct Brand is VuTan and Role is DN - Change Direct Brand to VuTan Distributor and keep Role as DN
            ("VuTan", "DN", "VuTan Distributor", "DN"),
            # If Direct Brand is TechnoTan Wholesale and Role is XDN - Keep direct brand as is and change Role to WN
            ("TechnoTan Wholesale", "XDN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand and Role is blank - Change Direct Brand to Pending and Role to RN
            ("", "", "Pending", "RN"),
            # If Direct Brand is Pending  and Role is RP - Change Role to RN
            ("Pending", "RP", "Pending", "RN"),
            # If Direct Brand is Pending  and Role is WN - Change Role to RN
            ("Pending", "WN", "Pending", "RN"),
            # If Direct Brand is Mosiac Minerals and Role is WN - Change Direct Brand to Mosaic Minerals Retail and Role to RN
            ("Mosaic Minerals", "WN", "Mosaic Minerals Retail", "RN"),

            # What about these?
                # 'Mosaic Minerals;TechnoTan': 38,
                # 'Mosaic Minerals;VuTan': 8,
                # 'TechnoTan;VuTan': 4,
                # 'Pending;VuTan Wholesale': 3,
                # 'TechnoTan;VuTan;': 2,
                # 'Pending;TechnoTan': 2,
                # 'TechnoTan Wholesale;VuTan Wholesale': 1,
                # 'Tanbience;TechnoTan Wholesale': 1,
                # 'Technotan Retail;VuTan Wholesale': 1,
                # 'TechnoTan Wholesale;Mosaic Minerals': 1,
                # 'TechnoTan Wholesale;': 1,
                # 'TechnoTan Distributor;': 1

            # How does it handle these:
                # TechnoTanRetail
        ]:
            result_brand, result_role = jess_fix(direct_brands, role)
            try:
                self.assertEqual(result_brand, expected_brand)
                self.assertEqual(result_role, expected_role)
            except Exception, exc:
                raise AssertionError("failed %s because of exception %s" % (
                    (direct_brands, role, expected_brand, expected_role),
                    str(exc)
                ))

if __name__ == '__main__':
    unittest.main()
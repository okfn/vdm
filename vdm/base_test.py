from base import *

class TestGetAttributeNames:

    def test_1(self):
        class X:
            class sqlmeta:
                columns = { 
                        'id' : None,
                        'name' : None,
                        'licenseID' : None,
                        'revisionID' : None,
                        'base' : None,
                        }
        out = get_attribute_names(X) 
        exp = [ 'id', 'name', 'license' ]
        assert set(out) == set(exp)

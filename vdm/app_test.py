from app import SimpleApplication
application = SimpleApplication()

class TestApplication:

    reg = application.registry

    def test_1(self):
        assert self.reg is not None


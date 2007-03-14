from app import application

class TestApplication:

    def test_1(self):
        myapp = application
        # usually only need do this once
        # but as using sqlite:/:memory: we do it every time
        myapp.initialise()
        reg = myapp.registry
        print reg

    # inner domain model and out domain model
    # 2 conceptual layers ...
    def test_2(self):
        myapp = application


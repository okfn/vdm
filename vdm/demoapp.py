from repository import *

class MyModelBuilder(SimpleModelBuilder):
    
    def construct(self):
        super(MyModelBuilder, self).construct()
        # do more

class MyBuilder(SimpleBuilder):

    def findModelBuilder(self):
        return MyModelBuilder()

class MyRepository(Repository):
    builderClass = MyBuilder()

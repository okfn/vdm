import dm.application
import dm.builder
from dm.ioc import *

class SysDict(dict):

    def __init__(self):
        self['logging.level'] = 'DEBUG'
        self['logging.log_file'] = './log.txt'
        self['system_name'] = 'blah'
        self['db.uri'] = 'sqlite:/:memory:'
        self['db.type'] = 'sqlite'


import dm.dom.builder
class MyModelBuilder(dm.dom.builder.ModelBuilder):

    registry = RequiredFeature('DomainRegistry')
    dictionary = RequiredFeature('SystemDictionary')

    def construct(self):
        pass

class MyPluginController:

    def notify(self, *args, **kwargs):
        # do nothing
        pass


class MyBuilder(dm.builder.ApplicationBuilder):

    def findSystemDictionary(self):
        return SysDict()

    def findFileSystem(self):
        return None

    def findModelBuilder(self):
        return MyModelBuilder()

    def findPluginController(self):
        return MyPluginController()


class Application(dm.application.Application):
    "Provides single entry point for clients."

    builderClass = MyBuilder

    def initialise(self):
        pass

# ensure only exists ...
application = Application()

import dm.application
import dm.builder
import dm.dom.builder
from dm.ioc import *

class SysDict(dict):

    def __init__(self):
        # set some defaults
        self['logging.level'] = 'DEBUG'
        self['logging.log_file'] = './log.txt'
        self['system_name'] = 'blah'
        self['db.uri'] = 'sqlite:/:memory:'
        self['db.type'] = 'sqlite'

class SimplePluginController:

    def notify(self, *args, **kwargs):
        # do nothing
        pass

class SimpleModelBuilder(dm.dom.builder.ModelBuilder):

    registry = RequiredFeature('DomainRegistry')
    dictionary = RequiredFeature('SystemDictionary')

    def construct(self):
        pass

class SimpleBuilder(dm.builder.ApplicationBuilder):

    def findSystemDictionary(self):
        return SysDict()

    def findFileSystem(self):
        # stub it as we do not need it
        return None

    def findModelBuilder(self):
        return SimpleModelBuilder()

    def findPluginController(self):
        return SimplePluginController()

import dm.application
class SimpleApplication(dm.application.Application):

    builderClass = SimpleBuilder

# application = SimpleApplication()

from elixir import *

from elixir.ext.versioned import acts_as_versioned
import vdm.elixir.complex as cx

from datetime import datetime, timedelta
import time

def setup():
    global Director, Movie, Actor

    class Director(Entity):
        has_field('name', Unicode(60))
        has_many('movies', of_kind='Movie', inverse='director')
        using_options(tablename='directors')


    class Movie(Entity):
        has_field('id', Integer, primary_key=True)
        has_field('title', Unicode(60), primary_key=True)
        has_field('description', Unicode(512))
        has_field('releasedate', DateTime)
        belongs_to('director', of_kind='Director', inverse='movies')
        has_and_belongs_to_many('actors', of_kind='Actor', inverse='movies', tablename='movie_casting')
        using_options(tablename='movies')
        cx.acts_as_versioned()


    class Actor(Entity):
        has_field('name', Unicode(60))
        has_and_belongs_to_many('movies', of_kind='Movie', inverse='actors', tablename='movie_casting')
        using_options(tablename='actors')

    setup_all()
    metadata.bind = 'sqlite:///'


def teardown():
    cleanup_all()

import sqlalchemy
class TestVersioning(object):
    def setup(self):
        create_all()
    
    def teardown(self):
        drop_all()
        objectstore.clear()
    
    def test_versioning(self):
        print '=== START: revision 1'
        rev1 = cx.Revision()
        rev1.log_message = 'Revision 1'
        assert rev1.session
        assert rev1.session.revision == rev1

        gilliam = Director(name='Terry Gilliam')
        monkeys = Movie(id=1, title='12 Monkeys', description='draft description', director=gilliam)
        bruce = Actor(name='Bruce Willis', movies=[monkeys])
        rev1.commit()
        objectstore.clear()

        rev1out = cx.Revision.get_by(id=1)
        movie = Movie.get_by(title='12 Monkeys')
        assert movie.revision == rev1out
        objectstore.clear()
    
        time.sleep(1)
        after_create = datetime.now()
        time.sleep(1)

        print '=== START: revision 2'
        rev2 = cx.Revision()
        rev2.log_message = 'Revision 2'

        movie = Movie.get_by(title='12 Monkeys')
        assert movie.title == '12 Monkeys'
        assert movie.director.name == 'Terry Gilliam'
        movie.description = 'description two'
        rev2.commit()
        # objectstore.flush();
        objectstore.clear()

        rev2out = cx.Revision.get(2)
        movie = Movie.get_by(title='12 Monkeys')
        assert movie.revision == rev2out
        objectstore.clear()

        time.sleep(1)
        after_update_one = datetime.now()
        time.sleep(1)

        rev3 = cx.Revision()
        rev3.log_message = 'Revision 3'
        movie = Movie.get_by(title='12 Monkeys')
        movie.description = 'description three'
        rev3.commit()
        # objectstore.flush();
        objectstore.clear()
    
        time.sleep(1)
        after_update_two = datetime.now()
        time.sleep(1)

        rev3out = cx.Revision.get(3)
        movie = Movie.get_by(title='12 Monkeys')
        assert movie.revision is not None
        assert movie.revision == rev3out
        objectstore.clear()
    
        movie = Movie.get_by(title='12 Monkeys')
        oldest_version = movie.get_as_of(after_create)
        middle_version = movie.get_as_of(after_update_one)
        latest_version = movie.get_as_of(after_update_two)
    
        initial_timestamp = oldest_version.timestamp
    
        assert oldest_version.revision_id == 1
        assert oldest_version.description == 'draft description'
    
        assert middle_version.revision_id == 2
        assert middle_version.description == 'description two'
    
        assert latest_version.revision_id == 3
        assert latest_version.description == 'description three'
    
        differences = latest_version.compare_with(oldest_version)
        assert differences['description'] == ('description three', 'draft description')
    
        print len(movie.versions)
        assert len(movie.versions) == 3
        assert movie.versions[0] == oldest_version
        assert movie.versions[1] == middle_version
    
#        movie.revert_to(1)
#        objectstore.flush(); objectstore.clear()
#    
#        movie = Movie.get_by(title='12 Monkeys')
#        assert movie.version == 1
#        assert movie.timestamp == initial_timestamp
#        assert movie.title == '12 Monkeys'
#        assert movie.director.name == 'Terry Gilliam'



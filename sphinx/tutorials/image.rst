Image & Thumbnails
==================

This is how to attach image file to sqlalchemy model using the :class:`.FileSystemStore`.

0. Prerequisites
----------------

Thumbnail generation required the ``wand``, and content type detection required ``magic`` package.
These are optional packages. so you have to install them:

.. code-block:: console

   $ pip install wand python-magic


1. Creating workbench
---------------------

Setting up and ``engine`` along-side the ``session_factory``. And creating a constant for the directory to store files.

..  testcode:: quickstart

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.declarative import declarative_base

    TEMP_PATH = '/tmp/sqlalchemy-media'
    Base = declarative_base()
    engine = create_engine('sqlite:///:memory:', echo=False)
    session_factory = sessionmaker(bind=engine)


2. Storage
----------

Registering a default factory for :class:`.FileSystemStore` class. the :class:`.StoreManager` will call it when needed.

..  testcode:: quickstart

    import functools

    from sqlalchemy_media import StoreManager, FileSystemStore

    StoreManager.register(
        'fs',
        functools.partial(FileSystemStore, TEMP_PATH, 'http://static.example.org/'),
        default=True
    )

3. Backend Type
---------------

We are using the sqlite's memory db in this tutorial, because it's so handy. but it's not supporting the JSON data type,
So, this is how to emulate a type using the
`SqlAlchemy Type Decorators <http://docs.sqlalchemy.org/en/latest/core/custom_types.html#typedecorator-recipes>`_.

..  testcode:: quickstart

    import json

    from sqlalchemy import TypeDecorator, Unicode

    class Json(TypeDecorator):
        impl = Unicode

        def process_bind_param(self, value, engine):
            return json.dumps(value)

        def process_result_value(self, value, engine):
            if value is None:
                return None

            return json.loads(value)


.. note:: You can use any type to store dictionary and list as described on top, but the postgreSql ``HStore`` and
          ``JSON`` are preferred.


4. Defining The Model
---------------------

As described in
`Sqlalchemy's documentation <http://docs.sqlalchemy.org/en/latest/orm/extensions/mutable.html#sqlalchemy.ext.mutable.Mutable.as_mutable>`_,
the ``as_mutable`` method is used to make a type mutable.

..  testcode:: quickstart

    from sqlalchemy import Column, Integer

    from sqlalchemy_media import Image, ImageAnalizer, ImageValidator, ImageProcessor

    class ProfileImage(Image):
        __pre_processors__ = [
            ImageAnalizer(),
            ImageValidator(
                minimum=(80, 80),
                maximum=(800, 600),
                min_aspect_ratio=1.2,
                content_types=['image/jpeg', 'image/png']
            ),
            ImageProcessor(
                fmt='jpeg',
                width=120,
                crop=dict(
                    left='10%',
                    top='10%',
                    width='80%',
                    height='80%',
                )
            )
        ]

    class Person(Base):
        __tablename__ = 'person'

        id = Column(Integer, primary_key=True)
        name = Column(Unicode(100))
        image = Column(ProfileImage.as_mutable(Json))

        def __repr__(self):
            return "<%s id=%s>" % (self.name, self.id)

5. DB Schema
------------

Making database objects using the famous function ``create_all``, and creating a session instance to interact with
database.

..  testcode:: quickstart

    Base.metadata.create_all(engine, checkfirst=True)
    session = session_factory()


6. Action !
-----------


..  testcode:: quickstart

    with StoreManager(session):
        person1 = Person()
        person1.image = ProfileImage.create_from('https://www.python.org/static/img/python-logo@2x.png')
        session.add(person1)
        session.commit()

        print('Content type:', person1.image.content_type)
        print('Extension:', person1.image.extension)
        print('Length:', person1.image.length)
        print('Original filename:', person1.image.original_filename)

..  testoutput:: quickstart

    Content type: image/jpeg
    Extension: .jpg
    Length: 2020
    Original filename: https://www.python.org/static/img/python-logo@2x.png


7. Thumbnails
-------------

..  testcode:: quickstart

    from os.path import exists, join

    with StoreManager(session):
        thumbnail = person1.image.get_thumbnail(width=32, auto_generate=True)
        print(thumbnail.height)
        assert exists(join(TEMP_PATH, thumbnail.path))

The thumbnail height is:

..  testoutput:: quickstart

    8


.. note:: If your delete an image using instructions bellow, all thumbnails will be deleted also.

..  warning:: Remember to commit the sqlalchemy's ``session`` after thumbnail generation to store the info, it's also
              can rollbacks the operation if transaction failed.


Generating thumbnail with ``ratio``

..  testcode:: quickstart

    from os.path import exists, join

    with StoreManager(session):
        thumbnail = person1.image.get_thumbnail(ratio=.3, auto_generate=True)
        print(thumbnail.width, thumbnail.height)
        assert exists(join(TEMP_PATH, thumbnail.path))

..  testoutput:: quickstart

    28 7

Call ``person1.image.locate()`` or ``person1.image.get_thumbnail(width=32, auto_generate=True).locate()`` to get the
files URL in store.

8. Overwriting
--------------

Overwriting a file is achieved by attaching an image by :meth:`.attach`

..  testcode:: quickstart

    with StoreManager(session):
        person1.image.attach('https://www.python.org/static/img/python-logo.png')
        session.commit()

        print('Content type:', person1.image.content_type)
        print('Extension:', person1.image.extension)
        print('Length:', person1.image.length)
        print('Original filename:', person1.image.original_filename)

..  testoutput:: quickstart

    Content type: image/jpeg
    Extension: .jpg
    Length: 2080
    Original filename: https://www.python.org/static/img/python-logo.png


9. Deleting & Delete Orphan
---------------------------

Set the model's attribute to :data:`.None`, while ``delete_orphan=True`` passed to :class:`.StoreManager`.

..  testcode:: quickstart

    with StoreManager(session, delete_orphan=True):
        deleted_filename = join(TEMP_PATH, person1.image.path)
        person1.image = None
        session.commit()

        assert not exists(deleted_filename)


Another way is to re-set the attribute using new instance:

..  testcode:: quickstart

    with StoreManager(session, delete_orphan=True):
        person1.image = ProfileImage.create_from('https://www.python.org/static/img/python-logo.png')
        session.commit()

        print('Content type:', person1.image.content_type)
        print('Extension:', person1.image.extension)
        print('Length:', person1.image.length)
        print('Original filename:', person1.image.original_filename)


..  testoutput:: quickstart

    Content type: image/jpeg
    Extension: .jpg
    Length: 2080
    Original filename: https://www.python.org/static/img/python-logo.png


..  warning:: Setting SqlAlchemy model's attribute without enabling ``delete_orphan`` will cause the orphaned files
              remaining in store for ever.

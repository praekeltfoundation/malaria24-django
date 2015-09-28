malaria24
=========================

This is an application scaffold for Molo_.
The Molo bits have been ripped out though as this is largely a headless
application with only a Django CMS.

Getting started
---------------

To get started::

    $ virtualenv ve
    $ pip install -e git+git://github.com/onaio/onapie.git#egg=onapie
    $ pip install -e .
    $ ./manage.py migrate
    $ ./manage.py createsuperuser
    $ ./manage.py runserver

You can now connect access the demo site on http://localhost:8000


.. _Molo: https://molo.readthedocs.org

.. Melissi Desktop Client documentation master file, created by
   sphinx-quickstart on Wed Jul 13 16:33:45 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Melissi Desktop Client's documentation!
==================================================

Contents:

.. toctree::
   :maxdepth: 2

About
=====

Melissi Desktop is a client for `Melissi Cloud Storage Server
<http://www.github.com/melissiproject/server>`_. Provides file
sychronization between the server (aka *Hive*) and your desktop, so
that files are automatically transferred / updated between the two.

To use Melissi Desktop you need a Hive account. If you don't have an
account you can setup your own Hive to host your files by following
the `Hive Installation Instructions
<http://melissi-server.readthedocs.org/en/latest/>`_.

If you already have a Hive account you are welcome to proceed with the
client installation.

Installing
==========

Things To Know
--------------

Melissi client is currently *alpha* software. Things may not work as expected.

  .. warning::

     Until the desktop client reaches a level of maturity **do not**
     use this software to handle files that you don't have
     backups. This software does delete and overwrite files on your
     filesystem.

Debian
------

1. Add our repositories to your sources.list and update

 ::

 ~$ sudo "echo 'deb http://packages.melissi.org/ sid main' >> /etc/apt/sources.list"
 ~$ sudo apt-get update

2. Install Melissi

  ::

  ~$ sudo apt-get install melissi

Fedora
------

Looking for a polite fedora packager ;)


The Python Way
--------------

Fetch the source code from the repository

 ::

 ~$ git clone http://github.com/melissiproject/client

Install

 ::

 ~$ cd client
 ~$ sudo python setup.py install


Running Desktop Client
======================

Desktop Menu
------------

Go to Menu->Internet->Melissi File Synchronization


Terminal
--------

If you run on a headless system (e.g. a server) or you don't want
melissi to attach to your desktop, you can still get melissi!

 ::

 ~$ melissi --no-desktop

 .. warning::

    You still need to create the initial configuration file using the
    desktop version. This issue `is already reported
    <https://github.com/melissiproject/client/issues/4>`_.

Contributing
============

Melissi Project depends heavily on your contribution. You can help the
development simply by using Melissi Desktop Client and reporting bugs
to `our issue tracking system on github
<http://www.github.com/melissiproject/client/issues/>`_ or, even
better, by submitting patches that fix bug or introduce new features.

All development is done on github under `melissi project
<http://www.github.com/melissiproject>`_ so can easily fork and develop.

You can post comments, questions and patches also on our developer's
mailing list `melissi-dev
<http://lists.melissi.org/cgi-bin/mailman/listinfo/melissi-dev>`_.


Community
=========

* `Melissi Project Website <http://www.melissi.org>`_

* `@melissiproject <http://www.twitter.com/melissiproject/>`_ twitter and `@melissiproject <http://identi.ca/melissiproject>`_

* #melissiporject on freenode

* `melissi-announce <http://lists.melissi.org/cgi-bin/mailman/listinfo/melissi-announce>`_  mailing list for the news



.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

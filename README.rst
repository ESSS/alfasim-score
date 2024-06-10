===============
ALFAsim Score
===============


.. image:: https://img.shields.io/pypi/v/alfasim-score.svg
    :target: https://pypi.python.org/pypi/alfasim-score

.. image:: https://img.shields.io/pypi/pyversions/alfasim-score.svg
    :target: https://pypi.org/project/alfasim-score

.. image:: https://github.com/ESSS/alfasim-score/workflows/test/badge.svg
    :target: https://github.com/ESSS/alfasim-score/actions

.. image:: https://codecov.io/gh/ESSS/alfasim-score/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/ESSS/alfasim-score

.. image:: https://img.shields.io/readthedocs/alfasim-score.svg
    :target: https://alfasim-score.readthedocs.io/en/latest/

.. image:: https://sonarcloud.io/api/project_badges/measure?project=ESSS_alfasim-score&metric=alert_status
    :target: https://sonarcloud.io/project/overview?id=ESSS_alfasim-score


What is alfasim-score?
=======================

Python package to convert the SCORE input JSON to Alfacase (ALFAsim input file).


Features
-----------

* Converter from Score input JSON to Alfacase
* Parser for the ALFAsim results


Development
-----------

For complete description of what type of contributions are possible,
see the full `CONTRIBUTING <CONTRIBUTING.rst>`_ guide.

Here is a quick summary of the steps necessary to setup your environment to contribute to ``alfasim-score``.

#. Create a virtual environment and activate it::

    $ python -m virtualenv .env
    $ .env\Scripts\activate  # windows
    $ source .env/bin/activate  # linux


   .. note::

       If you use ``conda``, you can install ``virtualenv`` in the root environment::

           $ conda install -n root virtualenv

       Don't worry as this is safe to do.

#. Update ``pip``::

    $ python -m pip install -U pip

#. Install development dependencies::

    $ pip install -e .[testing]

#. Install pre-commit::

    $ pre-commit install

#. Run tests::

    $ pytest --pyargs alfasim_score

#. Generate docs locally::

    $ tox -e docs

   The documentation files will be generated in ``docs/_build``.

Release
-------

A reminder for the maintainers on how to make a new release.

Note that the VERSION should folow the semantic versioning as X.Y.Z
Ex.: v1.0.5

1. Create a ``release-VERSION`` branch from ``upstream/master``.
2. Update ``CHANGELOG.rst``.
3. Push a branch with the changes.
4. Once all builds pass, push a ``VERSION`` tag to ``upstream``.
5. Merge the PR.


.. _`GitHub page` :                   https://github.com/ESSS/alfasim-score
.. _pytest:                           https://github.com/pytest-dev/pytest
.. _tox:                              https://github.com/tox-dev/tox

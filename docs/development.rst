Development
==================================

Development environment is managed with poetry.

.. code-block:: console

   $ git clone https://github.com/Velocidensity/serializd-py
   $ cd shorty
   $ poetry install --with-dev

------------------------------
Pre-commit hooks
------------------------------

To install pre-commit hooks, run:

.. code-block:: console

   $ pre-commit install

------------------------------
Building documentation
------------------------------

To build docs, install sphinx and furo theme with poetry, and then use make.

.. code-block:: console

   $ poetry install --with=docs
   $ cd docs
   $ make html

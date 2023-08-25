Installation and usage
==================================

------------------------------
Installation
------------------------------

.. code-block:: console

   $ pip install git+https://github.com/Velocidensity/serializd-py

Optionally with a virtual environment of your choice.

------------------------------
Usage example
------------------------------

>>> from serializd import SerializdClient
>>> client = SerializdClient()
>>> client.login(email="EMAIL", password="PASSWORD")  # optional for get_show()
>>> client.get_show(114472)
{'id': 114472, 'name': ...

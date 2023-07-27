# Serializd-py
Python API library for Serializd.com

# Features
- User authentication
- Fetching show/season information
- Logging shows and individual seasons as watched
- Full typing and documentation
- HTTP/2 with httpx

# Documentation
https://velocidensity.github.io/serializd-py/

# Usage example
```py
>>> from serializd import SerializdClient
>>> client = SerializdClient()
>>> client.login(email="EMAIL", password="PASSWORD")  # optional for get_show()
>>> client.get_show(114472)
{'id': 114472, 'name': ...
```

# Installation
```
pip install git+https://github.com/Velocidensity/serializd-py
```
Optionally with a virtual environment of your choice.

# Development
Development environment is managed via poetry.

```
poetry install --with=dev
```

To install pre-commit hooks, run:
```
pre-commit install
```

To build docs, install sphinx and furo theme with poetry, and then use make.
```
poetry install --with=docs
cd docs
make html
```

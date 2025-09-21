.PHONY: zip test lint format

zip:
python tools/make_zip.py

test:
pytest

lint:
ruff check addons/ai_modeler

format:
black addons/ai_modeler

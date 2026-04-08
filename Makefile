install:
	pip install -r requirements.txt
	pip install .

test:
	pip install pytest pytest-cov
	pytest --cov=hashtheplanet tests/

lint:
	pip install pylint
	python3 -m pylint hashtheplanet/ tests/

clean:
	rm -rf dist/*_hash_files.json

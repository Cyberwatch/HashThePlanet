install:
	pip install --no-deps -r requirements.txt
	pip install --no-deps .

test:
	pip install pytest pytest-cov
	pytest --cov=hashtheplanet tests/

lint:
	pip install pylint
	python3 -m pylint hashtheplanet/ tests/

clean:
	rm dist/*.db

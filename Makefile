install:
	pip install --no-deps -r requirements.txt
	pip install --no-deps .

test:
	pip install pytest pytest-cov
	pytest --cov=lib tests/

lint:
	pip install pylint
	python3 -m pylint lib/ tests/

clean:
	rm dist/*.db

install:
	pip install --no-deps -r requirements.txt
	pip install --no-deps .

clean:
	rm dist/*.db

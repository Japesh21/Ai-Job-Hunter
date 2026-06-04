.PHONY: install run-all scrape match report schedule test docker-build docker-up clean

install:
	pip install -r requirements.txt

scrape:
	python main.py scrape

match:
	python main.py match

report:
	python main.py report

run-all:
	python main.py all

schedule:
	python main.py schedule

test:
	pytest tests/ -v --cov=. --cov-report=term-missing

docker-build:
	docker build -t ai-job-hunter .

docker-up:
	docker compose up -d

docker-logs:
	docker compose logs -f

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

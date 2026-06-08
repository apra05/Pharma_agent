ifeq (,$(wildcard philoagents-api/.env))
$(error .env file is missing at philoagents-api/.env. Please create one based on .env.example)
endif

include philoagents-api/.env

# --- Infrastructure ---

infrastructure-build:
	docker compose build

infrastructure-up:
	docker compose up --build -d

infrastructure-stop:
	docker compose stop

check-docker-image:
	@python3 -c "import subprocess, sys; (subprocess.run(['docker', 'image', 'inspect', 'philoagents-course-api'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0) or (print('Error: philoagents-course-api Docker image not found.\nPlease run make infrastructure-build first to build the required images.') or sys.exit(1))"

# --- Offline Pipelines ---

MONGO_DOCKER_URI = mongodb://philoagents:philoagents@local_dev_atlas:27017/?directConnection=true

call-agent: check-docker-image
	docker run --rm --network=philoagents-network --env-file philoagents-api/.env -e MONGO_URI=$(MONGO_DOCKER_URI) -v ./philoagents-api/data:/app/data philoagents-course-api uv run python -m tools.call_agent --philosopher-id "turing" --query "How can we know the difference between a human and a machine?"

create-long-term-memory: check-docker-image
	docker run --rm --network=philoagents-network --env-file philoagents-api/.env -e MONGO_URI=$(MONGO_DOCKER_URI) -v ./philoagents-api/data:/app/data philoagents-course-api uv run python -m tools.create_long_term_memory

delete-long-term-memory: check-docker-image
	docker run --rm --network=philoagents-network --env-file philoagents-api/.env -e MONGO_URI=$(MONGO_DOCKER_URI) philoagents-course-api uv run python -m tools.delete_long_term_memory

generate-evaluation-dataset: check-docker-image
	docker run --rm --network=philoagents-network --env-file philoagents-api/.env -e MONGO_URI=$(MONGO_DOCKER_URI) -v ./philoagents-api/data:/app/data philoagents-course-api uv run python -m tools.generate_evaluation_dataset --max-samples 15

evaluate-agent: check-docker-image
	docker run --rm --network=philoagents-network --env-file philoagents-api/.env -e MONGO_URI=$(MONGO_DOCKER_URI) -v ./philoagents-api/data:/app/data philoagents-course-api uv run python -m tools.evaluate_agent --workers 1 --nb-samples 15

evaluate-agent-evidently: check-docker-image
	docker run --rm --network=philoagents-network --env-file philoagents-api/.env -e MONGO_URI=$(MONGO_DOCKER_URI) -v ./philoagents-api/data:/app/data -v ./philoagents-api/workspace:/app/workspace philoagents-course-api uv run python -m tools.evaluate_agent_evidently --workers 1 --nb-samples 15 --output-html data/evidently_report.html --output-json data/evidently_report.json


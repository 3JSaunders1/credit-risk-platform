SHELL := /bin/bash

# Locations of the two source projects (override on the command line if needed)
CREDIT_DEFAULT_DIR ?= $(HOME)/Desktop/credit_default_model_project
MACRO_LAB_DIR      ?= $(HOME)/Desktop/credit_model_project
export CREDIT_DEFAULT_DIR MACRO_LAB_DIR

.PHONY: all inputs stress dashboard test docker-build docker-test docker-run

all: stress

inputs:        ## Collect and validate artifacts from both projects into data/
	python -m platform_core.build_inputs

stress:        ## Run every macro scenario through the loan portfolio
	python -m platform_core.run_stress

dashboard:     ## Start the Streamlit dashboard
	python -m streamlit run dashboard/app.py

test:          ## Run the test suite
	python -m pytest -v

docker-build:  ## Build the Docker image
	docker build -t credit-risk-platform .

docker-test: docker-build   ## Run the test suite inside the container
	docker run --rm credit-risk-platform python -m pytest -q

docker-run: docker-build    ## Serve the dashboard from the container at http://localhost:8501
	docker run --rm -p 8501:8501 credit-risk-platform

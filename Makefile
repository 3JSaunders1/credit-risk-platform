SHELL := /bin/bash

# Locations of the two source projects (override on the command line if needed)
CREDIT_DEFAULT_DIR ?= $(HOME)/Desktop/credit_default_model_project
MACRO_LAB_DIR      ?= $(HOME)/Desktop/credit_model_project
export CREDIT_DEFAULT_DIR MACRO_LAB_DIR

.PHONY: all inputs stress test

all: stress

inputs:   ## Collect and validate artifacts from both projects into data/
	python -m platform_core.build_inputs

stress:   ## Run every macro scenario through the loan portfolio
	python -m platform_core.run_stress

test:     ## Run the test suite
	python -m pytest -v

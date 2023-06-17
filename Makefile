
.PHONY: build
build:
	docker build . -t openai-shell --output=bin --target=binaries

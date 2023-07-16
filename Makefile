
.PHONY: build
build:
	docker build . -t pherguson --output=bin --target=binaries

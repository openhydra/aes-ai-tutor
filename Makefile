REGISTRY ?= registry.cn-shanghai.aliyuncs.com/openhydra

IMAGETAG ?= $(shell git rev-parse --abbrev-ref HEAD)-$(shell git rev-parse --verify HEAD)-$(shell date -u '+%Y%m%d%I%M%S')
BRANCH ?= $(shell git branch --show-current)

.PHONY: image
image:
	docker build -t $(REGISTRY)/aes-ai-tutor:$(IMAGETAG) -f deploy/docker/Dockerfile . --load

.PHONY: image-then-push
image-then-push:
	docker build -t $(REGISTRY)/aes-ai-tutor:$(IMAGETAG) -f deploy/docker/Dockerfile . --load
	docker tag $(REGISTRY)/aes-ai-tutor:$(IMAGETAG) $(REGISTRY)/aes/aes-ai-tutor:$(BRANCH)
	docker push $(REGISTRY)/aes-ai-tutor:$(IMAGETAG)
	docker push $(REGISTRY)/aes-ai-tutor:$(BRANCH)
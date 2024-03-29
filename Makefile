SHELL = bash

NAME        := srl/custombase
LAST_COMMIT := $(shell sh -c "git log -1 --pretty=%h")
TODAY       := $(shell sh -c "date +%Y%m%d_%H%M")
TAG         := ${TODAY}.${LAST_COMMIT}
IMG         := ${NAME}:${TAG}
# HTTP_PROXY  := "http://proxy.server.com:8000"

ENHANCE_CLI ?= 1

ifndef SR_LINUX_RELEASE
override SR_LINUX_RELEASE=latest
endif

build: authorized_keys ssh_config # pygnmi
	DOCKER_BUILDKIT=1 docker build --build-arg SRL_CUSTOMBASE_RELEASE=${TAG} \
	   --build-arg http_proxy=${HTTP_PROXY} --build-arg https_proxy=${HTTP_PROXY} \
	   --build-arg SR_LINUX_RELEASE="${SR_LINUX_RELEASE}" \
	   --build-arg ENHANCE_CLI="${ENHANCE_CLI}" \
	   -f ./Dockerfile -t ${IMG} .
	sudo docker tag ${IMG} ${NAME}:${SR_LINUX_RELEASE}

pygnmi:
	rm -rf pygnmi
	git clone https://github.com/jbemmel/pygnmi.git
	cd pygnmi && DOCKER_BUILDKIT=1 docker build -t pygnmi .

authorized_keys:
	# Generate new SSH host key if not existing
	test -f ~/.ssh/id_rsa || ssh-keygen -h -q -t rsa -N '' -f ~/.ssh/id_rsa <<<y >/dev/null 2>&1
	cat ~/.ssh/id_rsa.pub > authorized_keys

ssh_config:
	test -f ~/.ssh/config || cp default_ssh_config ~/.ssh/config

rpm:
	docker run --rm -v $$(pwd):/tmp -w /tmp goreleaser/nfpm package \
	--config /tmp/nfpm.yml \
	--target /tmp/route-community-filter.rpm \
	--packager rpm


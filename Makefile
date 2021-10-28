SHELL = bash

NAME        := srl/custombase
LAST_COMMIT := $(shell sh -c "git log -1 --pretty=%h")
TODAY       := $(shell sh -c "date +%Y%m%d_%H%M")
TAG         := ${TODAY}.${LAST_COMMIT}
IMG         := ${NAME}:${TAG}
LATEST      := ${NAME}:latest
# HTTP_PROXY  := "http://proxy.server.com:8000"

ifndef SR_LINUX_RELEASE
override SR_LINUX_RELEASE="latest"
endif

build: authorized_keys ssh_config
	sudo DOCKER_BUILDKIT=1 docker build --build-arg SRL_CUSTOMBASE_RELEASE=${TAG} \
	   --build-arg http_proxy=${HTTP_PROXY} --build-arg https_proxy=${HTTP_PROXY} \
	   --build-arg SR_LINUX_RELEASE="${SR_LINUX_RELEASE}" \
	   -f ./Dockerfile -t ${IMG} .
	sudo docker tag ${IMG} ${LATEST}

authorized_keys:
	# Generate new SSH host key if not existing
	test -f ~/.ssh/id_rsa || ssh-keygen -h -q -t rsa -N '' -f ~/.ssh/id_rsa <<<y >/dev/null 2>&1
	cat ~/.ssh/id_rsa.pub > authorized_keys

define default_ssh_config
Host *
	StrictHostKeyChecking no
	UserKnownHostsFile /dev/null
endef
ssh_config:
	test -f ~/.ssh/config || \
	 (echo $(default_ssh_config) > ~/.ssh/config && chmod 400 ~/.ssh/config)

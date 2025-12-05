VERSION := v2

all: image

image: Dockerfile
	docker build . -t directangular/cert-alert:$(VERSION)

push: image
	docker push directangular/cert-alert:$(VERSION)

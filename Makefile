all: image

image: Dockerfile
	docker build . -t directangular/cert-alert

push: image
	docker push directangular/cert-alert

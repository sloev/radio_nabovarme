run:
	docker build -t robot . && docker run -d --restart=always --name=robot -eURL=192.168.43.67:8080 -p 8080:80 robot 

interactive:
	docker build -t robot . && docker run --rm -it --name=robot_interactive -eMQTT=nabovarme.meterlogger.net -eURL=192.168.0.102:8080 -p 8080:80 robot 

stop:
	docker kill robot && docker rm robot
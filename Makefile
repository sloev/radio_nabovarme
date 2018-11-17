run:
	docker build -t robot . && docker run -d --restart=always --name=robot -eURL=10.0.1.81:8080 -p 8080:80 robot 

interactive:
	docker build -t robot . && docker run --rm -it --name=robot_interactive -eURL=10.0.1.81:8080 -p 8080:80 robot 

stop:
	docker kill robot && docker rm robot
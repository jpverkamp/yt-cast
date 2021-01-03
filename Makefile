debug:
	docker build -t yt-cast .
	docker run -it -p 80:5000 -v $(shell pwd)/data:/app/data yt-cast
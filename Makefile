debug:
	docker build -t yt-cast .
	docker run -it -p 80:5000 yt-cast
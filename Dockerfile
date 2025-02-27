# Build the image with the Django web app
# docker build . -t django

# Locally deploy the web app to localhost:8000
# docker run -ti -p 8000:8000 django

# Run a shell within the context of the web app
# docker run -ti django python manage.py shell

# Run unit tests
# docker run -ti django python manage.py test

# Develop with local files
# docker run -ti -v $PWD:/usr/src/app -p 8000:8000 django
# docker run -ti -v $PWD:/usr/src/app django python manage.py shell
# docker run -ti -v $PWD:/usr/src/app django python manage.py test

FROM python:3.13

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		postgresql-client \
		diamond-aligner \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

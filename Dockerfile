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

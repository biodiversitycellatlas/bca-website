# Biodiversity Cell Atlas web app

The Biodiversity Cell Atlas is a coordinated international effort aimed at molecularly characterizing cell types across the eukaryotic tree of life. Our mission is to pave the way for the efficient expansion of cell atlases to hundreds of species.

## Overview

This project uses:

* [Docker Compose][compose] to manage multiple Docker containers
* [Django][django], a high-level Python web framework

### Initial setup

To setup the project and locally deploy the web app, follow these steps:

```bash
# Start Docker Compose to locally deploy the web app to localhost:8000
# - Prepares and downloads all Docker containers and starts the containers
# - `-d`: starts the Docker containers in detached mode
# - `--build web`: rebuilds the web image if needed (for instance, new Python
#   dependencies in `requirements.txt`)
docker compose up -d --build web

# Create a superuser (only required once for database setup)
docker compose exec web python manage.py createsuperuser
```

### Development

These are some of the commands to use during development:

```bash
# Start Docker Compose to locally deploy the web app to localhost:8000
docker compose up -d --build web

# Check information about the active Docker Compose containers
docker compose ps

# Check container logs
# - use `-f` to live update log output
# - add container name to print logs only for that container
docker compose logs
docker compose logs -f
docker compose logs web

# Run a bash shell within the Docker container for the web app
docker compose exec web bash

# Run a Python shell within the context of the web app: read
# https://docs.djangoproject.com/en/dev/intro/tutorial02/#playing-with-the-api
docker compose exec web python manage.py shell

# Run unit tests: read https://docs.djangoproject.com/en/dev/topics/testing/
docker compose exec web python manage.py test

# Stop and delete all containers and Docker networks
docker compose down
```

The project directory is automatically mounted to the web app container,
allowing the preview updates in the web app in real-time. However, to apply any
changes to Django models, you need to run the [`migrate`][migrate] command:

```bash
docker compose exec web python manage.py migrate
```

This command runs automatically when the web app container starts. As such, you
may simply restart the web app service to apply changes to Django models:

```bash
docker compose restart web
```

## Contact us

[<img src="web_app/static/web_app/images/CRG/LOGOs-CRG-ENG_2014_transparent_back.png" width="100" target="_blank" alt="Centre for Genomic Regulation (CRG)"/>][CRG]

[<img src="web_app/static/web_app/images/EMBL-EBI/EMBL-EBI_Logo_black_big.png" width="100" target="_blank" alt="European Bioinformatics Institute (EMBL-EBI)"/>][EBI]

[compose]: https://docs.docker.com/compose
[django]: https://www.djangoproject.com
[migrate]: https://docs.djangoproject.com/en/dev/topics/migrations/
[CRG]: https://www.crg.eu
[EBI]: https://www.ebi.ac.uk/

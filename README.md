# Pliro Project

This project is a Flask-based application with PostgreSQL and Redis, containerized using Docker.

## Prerequisites

Ensure you have the following installed on your system:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Setup and Installation

### 1. Clone the Repository

```sh
git clone https://github.com/mannan-quest/pliro_server.git
cd pliro_server
```

### 2. Create a `.env` File

Create a `.env` file in the project root with the following content:

```sh
POSTGRES_USER=abdulmannan
POSTGRES_PASSWORD=postgres
POSTGRES_DB=pliro_db
REDIS_URL=redis://redis:6379/0
FLASK_ENV=development
```

### 3. Build and Start the Containers

Run the following command to build and start the containers:

```sh
docker-compose up --build
```

### 4. Verify Running Containers

Check if all containers are running:

```sh
docker ps
```

You should see `flask_container`, `postgres_container`, and `redis_container` running.

### 5. Access the Application

- The Flask app runs on [**http://localhost:8000**](http://localhost:8000)
- PostgreSQL is accessible on port **5432**
- Redis is available on port **6379**

## Database Migrations

If needed, you can manually run database migrations inside the Flask container:

```sh
docker exec -it flask_container flask db upgrade
```

## Stopping the Application

To stop and remove containers, use:

```sh
docker-compose down
```

If you also want to remove volumes (erasing database data):

```sh
docker-compose down -v
```

## Debugging

### Check Logs

```sh
docker logs flask_container
```

```sh
docker logs postgres_container
```

### Connect to PostgreSQL Inside the Container

```sh
docker exec -it postgres_container psql -U abdulmannan -d pliro_db
```

### Check if Database is Reachable

```sh
docker exec -it flask_container bash
psql -h db -U abdulmannan -d pliro_db
```



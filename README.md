A RESTful API for vehicle inventory management built with FastAPI and PostgreSQL. Features full CRUD operations, input validation, and comprehensive error handling.

# To Run Locally

To run:

brew services start postgresql@17

export DATABASE_URL="postgresql://user:password@localhost:5432/vehicles_local"

uvicorn main:app --reload

To test:

pytest test_api.py -vv

# Run with Docker

To run:

docker-compose up --build

To run tests:

docker compose run --rm api pytest -vv test_api.py

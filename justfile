set dotenv-load

default:
    cd src; poetry run uvicorn main:app --reload

run:
    cd src; poetry run uvicorn main:app

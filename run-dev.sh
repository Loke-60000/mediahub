export $(grep -v '^#' .env | xargs)

mkdir -p $TEMP_DIR

uvicorn app.main:app --host $HOST --port $PORT --reload
docker run -d \
-p $POSTGRES_PORT:5432 \
-e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
-e PGDATA=/var/lib/postgresql/data/pgdata \
-e POSTGRES_USER=$POSTGRES_USER \
-v $POSTGRES_DATA:/var/lib/postgresql/data \
--name $POSTGRES_DOCKER_NAME \
--restart=always postgres:alpine
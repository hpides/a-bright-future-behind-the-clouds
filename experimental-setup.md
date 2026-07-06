## Starting the services

### Start & connect to a DB:

```docker compose -up <database_service>```

Current supported database services: postgres, umbra, duckdb  

### Connect to Umbra/Postgres

```psql -p 5434 -h 127.0.0.1 -U postgres```

### Run Benchbase with Postgres

``` 
docker compose --profile bench run --rm benchbase \
  -b tpcc \
  -c /work/config/postgres-tpcc.xml \
  --create=true \
  --load=true \
  --execute=true \
  -d /benchbase/results 
  
```
### Run Benchbase with Umbra

``` 
docker compose --profile bench run --rm benchbase \
  -b tpcc \
  -c /work/config/umbra-tpcc.xml \
  --create=true \
  --load=true \
  --execute=true \
  -d /benchbase/results 
  
```
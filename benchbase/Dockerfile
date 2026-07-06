FROM maven:3-eclipse-temurin-23 AS build

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN git clone --depth 1 https://github.com/cmu-db/benchbase.git

WORKDIR /src/benchbase

RUN mvn -T 2C -B --file pom.xml package \
    -Ddescriptors=src/main/assembly/dir.xml \
    -P postgres \
    -Dfmt.skip \
    -DskipTests \
    -Dmaven.test.skip=true \
    -Dmaven.javadoc.skip=true \
    -DbuildDirectory=target/postgres

RUN test -f target/postgres/benchbase-postgres/benchbase-postgres/benchbase.jar

FROM eclipse-temurin:23-jre

WORKDIR /benchbase

COPY --from=build \
  /src/benchbase/target/postgres/benchbase-postgres/benchbase-postgres/ \
  /benchbase/

RUN mkdir -p /work/config /benchbase/results

ENTRYPOINT ["java", "-jar", "/benchbase/benchbase.jar"]
CMD ["--help"]

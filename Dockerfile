FROM nikolaik/python-nodejs:python3.11-nodejs22

ENV PYTHONUNBUFFERED 1
COPY . /app
WORKDIR /app
RUN mkdir database
RUN npm install
RUN poetry install
RUN poetry run hyperflask assets build
RUN poetry run mkdocs build -d app/docs
ENTRYPOINT ["poetry", "run", "hyperflask"]
CMD ["run"]
EXPOSE 5000
VOLUME /app/database

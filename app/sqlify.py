import psycopg
from contextlib import contextmanager
from hyperflask import current_app
import csv
from io import StringIO


@contextmanager
def connect(database="system", username=None):
    connstr = f"postgresql://system:{current_app.config['SQLIFY_SYSTEM_PASSWORD']}@{current_app.config['SQLIFY_DOMAIN']}/{database}"
    with psycopg.connect(connstr) as conn:
        with conn.cursor() as cur:
            if username:
                cur.execute("SET ROLE %s", (username,))
            yield cur


def query(stmt, db="system", username=None):
      if stmt.startswith("USE"):
          return [], []
      with connect(db, username) as cur:
          cur.execute(stmt)
          results = cur.fetchall()
          columns = [c.name for c in cur.description]
          return results, columns


def get_connection_string(user, db):
    return f"postgresql://{user.db_role}:{user.db_password}@{current_app.config['SQLIFY_DOMAIN']}/{db}"


def iter_results_as_csv(results, columns=None):
    line = StringIO()
    writer = csv.writer(line)
    if columns:
        writer.writerow(columns)
        line.seek(0)
        yield line.read()
        line.truncate(0)
        line.seek(0)
    for row in results:
        writer.writerow(row)
        line.seek(0)
        yield line.read()
        line.truncate(0)
        line.seek(0)

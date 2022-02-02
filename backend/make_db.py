#so this whole thing is a bit of a weird workaround
#to be dealt with later
#literally just a single table at the moment
#ugh this makes me cringe
import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extensions import AsIs
import os
import datetime

load_dotenv()


def connect():
  #grab the environment variables
  db = os.environ.get("DB_NAME")
  user = os.environ.get("DB_USER")
  pwd = os.environ.get("DB_PASSWORD")
  host = os.environ.get("DB_HOST")

  #check if the DB already exists
  #if not, make it
  c1 = psycopg2.connect(user=user, password=pwd, host=host)
  cur1 = c1.cursor()
  try:
      c2 = psycopg2.connect(dbname=db, user=user, password=pwd, host=host)
  except psycopg2.OperationalError:
      c1.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
      cur1.execute('CREATE DATABASE {};'.format(db))
      c2 = psycopg2.connect(dbname=db, user=user, password=pwd, host=host)

  return c2


def main():
    con = connect()
    cur = con.cursor()

    #for the sake of this single use case, just throw everything into a single table
    #obviousle terrible practice
    cur.execute("DROP TABLE IF EXISTS consent_forms CASCADE;")

    cur.execute("""create table consent_forms (
        id serial primary key,
        redcap_id int,
        email varchar(256),
        consent_recording boolean,
        consent_surveys boolean,
        consent_twitter boolean,
        consent_linkedin boolean,
        consent_cv boolean,
        consent_quotations boolean,
        consent_email boolean,
        typed_consent varchar(512),
        signature_consent text,
        submitted_at timestamp
    )""")

    con.commit()

    path = os.environ.get("DATA_BASE_URL") + "/no_id_forms"
    if(not os.path.exists(path)):
        os.mkdir(path)

main()

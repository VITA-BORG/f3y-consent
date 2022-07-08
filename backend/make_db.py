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
import json

load_dotenv()

#load the config file
config = json.load(open("config.json"))


def connect():
  #grab the environment variables
  db = config["database"]
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

    #make the string
    #probably could be more efficient with some kind of buffer but anyway
    q = "create table consent_forms (id serial primary key,"

    if(config["redcap"]["enabled"]):
        q += "redcap_id int,"

    for elem in config["db_fields"]:
        q += "{} {},".format(elem["name"], elem["type"])

    q += "email varchar(256), submitted_at timestamp)"
    cur.execute(q)

    con.commit()

    path = config["files"]["base_location"] + "/no_id_forms"
    if(not os.path.exists(path)):
        os.mkdir(path)

main()

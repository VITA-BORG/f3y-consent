#for api
import flask
from flask import request, jsonify, Response, send_file
from flask_cors import CORS
from flask.json import JSONEncoder

#other useful things
import sys
import requests
import os
from dotenv import load_dotenv
import psycopg2
import redcap
from datetime import datetime
import base64
import json

#for pdf editing
import fitz

#for emailing
import email, smtplib, ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#some globals
#don't judge me, they're convenient and avoid repeated fetching
load_dotenv()
#could maybe later make this more flexible name wise and, y'know, do some actual error handling...
config = json.load(open("config.json"))

port = os.environ.get("API_PORT")
app = flask.Flask(__name__)
CORS(app)
app.config["DEBUG"] = True

#for db link, if needed
name = config["database"]
user = os.environ.get("DB_USER")
pwd = os.environ.get("DB_PASSWORD")
host = os.environ.get("DB_HOST")

con =psycopg2.connect(dbname=name, user=user, password=pwd, host=host)
cur = con.cursor()

base_url = config["files"]["base_location"]
rc_enabled = config["redcap"]["enabled"] if config.get("redcap") else None
if(rc_enabled):
    rc_api_url = config["redcap"].get("api_url")
    rc_api_key = config["redcap"].get("api_token")
    rc_project = redcap.Project(rc_api_url, rc_api_key)
form_elems = config["form_fields"]


sender = config["email"]["sender_email"]
email_subject = config["email"]["subject"]
email_template = config["email"]["template"]
#set up email server
context = ssl.create_default_context()




@app.route('/', methods=['GET'])
def home():
    return "api running"


#check that the email is valid
@app.route('/validate', methods=['POST'])
def verify():
    try:
        data  = flask.request.json["email"]
    except:
        return  Response("Validation error",status=500)
    cur.execute("select * from consent_forms where email = %s" , (data,))
    res = cur.fetchall()
    #should only ever be 1, but to stay on the safe side
    error = None if len(res)==0 else "We already have a consent form on record for that email"
    return jsonify({"error": error})

#do all the actual processing
@app.route('/submit', methods=['POST'])
def submit():
    try:
        data  = flask.request.json

    except:
        return  Response("Validation error",status=500)
    q = "insert into consent_forms({}) values ({})"
    param_names = ["email", "submitted_at"]
    params= [data["contact"]["email"],  datetime.now()]
    #fetch the redcap id
    redcap_id=None
    if(rc_enabled):
        redcap_id = getRedcapId(data["contact"]["email"])
        param_names.append("redcap_id")
        params.append(redcap_id)
    for elem in config["db_fields"]:
        try:
            param_names.append(elem["name"])
            params.append(data["consent"][elem["form_name"]])
        except:
            print(elem, data["consent"].keys())

    q = q.format(','.join(param_names), ','.join(["%s"]*len(params)))



    #add an entry to the database
    cur.execute(q , tuple(params))
    con.commit()
    #construct the pdf

    prefix = str(redcap_id) if redcap_id is not None else data["contact"]["email"].split("@")[0].replace(".", '')
    path = base_url + ("/{}".format(str(redcap_id)) if redcap_id is not None else "/no_id_forms")

    if redcap_id is not None:
        if not os.path.exists(path):
            os.mkdir(path)

    buildPdf(data["consent"], prefix, path)
    #some code duplication ugh
    ret_file = "{}/{}_consent.pdf".format(path, prefix)

    #send email if requested
    send = data.get("sendEmail")
    if(send):
        sendEmail(data["contact"]["email"], ret_file)

    #return the pdf in the response
    #so that it can be downloaded
    return  send_file(ret_file, mimetype='application/pdf')


#could be slow to fetch every time...but safer
#string has to match data dictionary
def getRedcapId(email):
    participants = rc_project.export_records(fields=['record_id','email_address'])
    for elem in participants:
        if elem['email_address']==email:
            return elem["record_id"]
    #unnecessary, but for the sake of clarity
    return None

def add_text_rect(text_val, page, loc):
    text_length = fitz.getTextlength(text_val, fontname="Helvetica", fontsize=config["fontsize"])
    rect = fitz.Rect(loc['x'], loc['y'], loc['x'] + text_length + 2, loc['y'] + config["fontsize"]+2 )
    page.insertTextbox(rect, text_val, fontsize = config["fontsize"], fontname = "Helvetica", align = 1)

def add_img_rect(img_path, page, loc):
    rect = fitz.Rect(loc['x'], loc['y'], loc['x']+config["sigsize"]["width"], loc['y']+config["sigsize"]["height"])
    page.insert_image(rect, filename = img_path)

def add_signature(sig, page, loc):
    f= open('signature.png', 'wb')
    sig = sig.split(",")[1]
    base64_img_bytes = sig.encode('utf-8')
    decoded_image_data = base64.decodebytes(base64_img_bytes)
    f.write(decoded_image_data)
    f.close()

    add_img_rect("signature.png", page, loc)

    os.system('rm signature.png')

def add_curr_date(format, page, loc):
    text = datetime.now().strftime(format)
    add_text_rect(text, page, loc)



#could probably have used lambda for this, but whatever
#leaning on default null return for unchecked boxes
def map_bool(b):
    if(b=='false'):
        return False
    elif(b=="true"):
        return True



def buildPdf(info, prefix, path):


    #load the appropriate template depending on whether or not they have a signature
    temp = config["files"]["template"]
    datestring = datetime.now().strftime('%Y/%m/%d')
    #put a copy in the current directory to manipulate, move it after
    os.system("cp {} consent.pdf".format(temp))
    #open the correct template
    doc = fitz.open("consent.pdf")
    #fill in all the values
    cur_page = config["form_fields"][0]["page"]
    page = doc.load_page(2)
    page.cleanContents()

    for elem in config["form_fields"]:
        val = info[elem["name"]] if elem["name"] in info else elem.get("value", None)
        if(elem["page"]!=cur_page):
            page = doc.load_page(2)
            page.cleanContents()
        #again wishing I had switch
        if(elem["type"]=='text'):
            add_text_rect(val, page, elem["coords"])
        elif(elem["type"]=='signature'):
            add_signature(val, page, elem["coords"])
        elif(elem['type']=='current_date'):
            add_curr_date(elem["format"], page, elem["coords"])
        elif(elem['type']=='image'):
            add_img_rect(val, page, elem["coords"])
        #untested for the time being
        elif(elem["type"]=='checkbox'):
            add_img_rect("./templates/checkmark.png", page, elem["coords"][map_bool(val)])

    #save in the appropriate location
    doc.save("{}/{}_consent.pdf".format(path, prefix))
    #not really necessary, but clean up
    os.system('rm consent.pdf')

#lots of code gratefully borrowed from here: https://realpython.com/python-send-email/
def sendEmail(email, path):
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context)
        server.login(sender, os.environ.get("SENDER_PASSWORD"))
    except Exception as e:
        #deal with errors on api boot up
        #not stellar error handling, but passable
        print(e)
        exit()
    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = email
    message["Subject"] = email_subject


    # Add body to email
    message.attach(MIMEText(email_template, "plain"))

    filename=config["email"]["attachment_name"]
    os.system("cp {} {}".format(path, filename))

    # Open PDF file in binary mode
    with open(filename, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email
    encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {filename}",
    )

    # Add attachment to message and convert message to string
    message.attach(part)
    text = message.as_string()
    server.sendmail(sender, email, text)

    #cleanup
    os.system("rm {}".format(filename))
    server.quit()



app.run(port=port)

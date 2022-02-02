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

#for pdf editing
import fitz

#for emailing
import email, smtplib, ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#some globals
#don't judge me, they're convenient
load_dotenv()

port = os.environ.get("API_PORT")
app = flask.Flask(__name__)
CORS(app)
app.config["DEBUG"] = True

#for db link, if needed
name = os.environ.get("DB_NAME")
user = os.environ.get("DB_USER")
pwd = os.environ.get("DB_PASSWORD")
host = os.environ.get("DB_HOST")
base_url = os.environ.get("DATA_BASE_URL")
con =psycopg2.connect(dbname=name, user=user, password=pwd, host=host)
cur = con.cursor()
rc_api_url = os.environ.get("REDCAP_API_URL")
rc_api_key = os.environ.get("REDCAP_API_TOKEN")
rc_project = redcap.Project(rc_api_url, rc_api_key)
location_maps = {"recording": {'true': {'x':155, 'y':629}, 'false':{'x':227, 'y':629}}, "surveys": {'true': {'x':155, 'y':661}, 'false':{'x':227, 'y':661}}, "twitter": {'true': {'x':155, 'y':177}, 'false':{'x':227, 'y':177}, 'null': {'x':300, 'y':177}}, 'linkedin':{'true': {'x':155, 'y':227}, 'false':{'x':227, 'y':227}, 'null': {'x':300, 'y':227}}, 'cv':{'true': {'x':155, 'y':263}, 'false':{'x':227, 'y':263}}, 'quotations':{'true': {'x':155, 'y': 313}, 'false':{'x':227, 'y':313}}, 'email':{'true': {'x':155, 'y':361}, 'false':{'x':227, 'y':361}}, 'name':{'x':155, 'y':515}, 'signature':{'x': 155, 'y':557} }


sender = os.environ.get("SENDER_EMAIL")
#set up email server
context = ssl.create_default_context()


email_subject = "The First Three Years - Study Consent Form"
email_template = """
Hello,

Please find attached a copy of your First Three Years study consent form. We are thrilled that you have chosen to participate in the project!

All the best,
The First Three Years Team
"""



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
    #fetch the redcap id
    redcap_id = getRedcapId(data["contact"]["email"])
    #add an entry to the database
    cur.execute("insert into consent_forms(redcap_id, email, consent_recording, consent_surveys, consent_twitter, consent_linkedin, consent_cv, consent_quotations, consent_email, typed_consent, signature_consent, submitted_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s )" , (redcap_id, data["contact"]["email"], map_bool(data["consent"]["recording"]),  map_bool(data["consent"]["surveys"]),  map_bool(data["consent"]["twitter"]),  map_bool(data["consent"]["linkedin"]),  map_bool(data["consent"]["cv"]),  map_bool(data["consent"]["quotations"]),  map_bool(data["consent"]["email"]), data["consent"].get("typed"), data["consent"].get("signature"), datetime.now() ))
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

def buildPdf(info, prefix, path):

    #load the appropriate template depending on whether or not they have a signature
    sig = info.get("signature")
    typed = info.get("typed")
    temp = "./templates/F3Y_FullStudyConsent" + (".pdf" if sig is not None else "_NameOnly.pdf" )
    #put a copy in the current directory to manipulate, move it after
    os.system("cp {} consent.pdf".format(temp))
    #open the correct template
    doc = fitz.open("consent.pdf")
    #fill in all the boxes
    #this is going to be shittily hardcoded, but what can you do
    #can't loop (really) b/c of pagebreak
    page = doc.load_page(5)
    page.cleanContents()
    for key in ['recording', 'surveys']:
        coords = location_maps[key][info[key]]
        rect = fitz.Rect(coords['x'], coords['y'], coords['x']+15, coords['y']+15)
        page.insert_image(rect, filename = "./templates/checkmark.png")
    page = doc.load_page(6)
    page.cleanContents()
    for key in ['twitter', 'linkedin','cv', 'quotations', 'email']:
        coords = location_maps[key][info[key]]
        rect = rect = fitz.Rect(coords['x'], coords['y'], coords['x']+15, coords['y']+15)
        page.insert_image(rect, filename = "./templates/checkmark.png")
    #add the name
    text_lenght = fitz.getTextlength(typed, fontname="Helvetica", fontsize=18)
    coords = location_maps["name"]
    rect = fitz.Rect(coords['x'], coords['y'], coords['x'] + text_lenght + 2, coords['y'] + 20 )
    page.insertTextbox(rect, typed, fontsize = 18, fontname = "Helvetica", align = 1)

    #signature (if applicable)
    if(sig):
        #save it to a file, to be renamed and moved like the pdf
        f= open('signature.png', 'wb')
        sig = sig.split(",")[1]
        base64_img_bytes = sig.encode('utf-8')
        decoded_image_data = base64.decodebytes(base64_img_bytes)
        f.write(decoded_image_data)
        f.close()
        coords = location_maps["signature"]
        rect = fitz.Rect(coords['x'], coords['y'], coords['x']+200, coords['y']+80)
        page.insert_image(rect, filename = "signature.png")


    #save in the appropriate location
    doc.save("{}/{}_consent.pdf".format(path, prefix))
    #not really necessary, but clean up
    os.system('rm consent.pdf')
    os.system('rm signature.png')

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

    os.system("cp {} f3y_consent.pdf".format(path))
    filename = "f3y_consent.pdf"  # In same directory as script

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
    os.system("rm f3y_consent.pdf")
    server.quit()




#could probably have used lambda fpr this, but whatever
def map_bool(b):
    if(b=='false'):
        return False
    elif(b=="true"):
        return True
    #another superfluous line for clarity
    return None



app.run(port=port)

### Configurable whitelabel consent form

This is meant to be a generic(ish) online consent form that can be ported to one project to another without needing to rewrite (almost) any code.
The functionality relies on not-exactly-trivial user supplied configuration, but it's not complicated either.

In brief, for a custom instance, you'll need to supply:

* A backend configuration file **config.json** -> it needs to go in the **backend/** directory
* A blank pdf version of the consent file -> location specified in backend config
* A front end configuration file **env.js** -> it needs to go in the **frontend/js** directory
* An HTML template of just the body text of the consent form (not anything that needs to be filled in) -> location specified in frontend configuration file
* Any images that need to appear on the webform (such as logos) or in the pdf (such as study personnel signatures)  (optional) -> locations specified in configuration files
* A second HTML template outlining instructions in the case that the user needs to take action (such as booking an interview) after the form (optional) ->  location specified in frontend configuration file


The backend configuration also includes connection information for the database. As part of the setup, you'll need to make sure that the relevant fields are filled and then run the make_db.py script to ... make the DB.

The way that the form currently works is that if the participant chooses not not have the form emailed to them, it will automatically download on completion.


#### Example backend configuration

Email supplied has to be gmail, and the settings need to have been changed to [open up the authentication](https://hotter.io/docs/email-accounts/secure-app-gmail/).  
There are four form field types: text, current_date, signature, and checkbox.  
'Type' fields in the db_fields section need to match up with postgres data types.
You can have more form fields than database fields (so that it it possible to only save unique/important values).  
Set redcap to enabled with the appropriate token/link if the consent forms will correspond to participants in a redcap project.  

```
{
   "database":"sop2",
   "fontsize":14,
   "sigsize": {"width":150, "height":60},
   "files":{
      "base_location":"/place_to_put_data",
      "form_location":"",
			"template":"./templates/consent_form.pdf"
   },
   "form_fields":[
      {
         "name":"participant_name",
         "coords":{
            "x":80,
            "y":270
         },
         "type":"text",
				 "page":3
      },
      {
         "name":"participant_signature",
         "coords":{
           "x":185,
           "y":250
         },
         "type":"signature",
				 "page":3
      },
      {
         "name":"participant_date",
         "coords":{
           "x":390,
           "y":270
         },
         "type":"current_date",
         "format":"%Y/%m/%d",
				 "page":3
      },
      {
         "name":"study_name",
         "coords":{
           "x":80,
           "y":333
         },
         "type":"text",
         "value":"Study Person",
				 "page":3
      },
      {
         "name":"study_signature",
         "coords":{
           "x":185,
           "y":308
         },
         "type":"image",
         "value":"./templates/study_sig.png",
				 "page":3
      },
      {
         "name":"study_date",
         "coords":{
           "x":390,
           "y":333
         },
         "type":"current_date",
         "format":"%Y/%m/%d",
				 "page":3
      }
   ],
   "db_fields":[
      {
         "name":"name",
         "form_name":"participant_name",
         "type":"varchar(255)"
      },
      {
         "name":"signature",
         "form_name":"participant_signature",
         "type":"text"
      }
   ],
   "email":{
      "attachment_name":"project_consent.pdf",
      "sender_email":"projectemail@ualberta.ca",
      "sender_password":"email_password",
			"subject":"Study - signed consent form",
			"template":"Hello,\n\nPlease find attached a copy of your consent form. We are thrilled that you have chosen to participate in the project!\n\nAll the best,\nThe Study Team",
			"attachment_name":""
   },
   "redcap":{
      "enabled":true,
      "api_token":"32 character alphanumeric token",
      "api_url":"https://redcap.ualberta.ca/api/"
   }
}
```


#### Example frontend configuration

You must include the trailing slash in the api url.  
Background colour is the form background, primary colour is for the form gutters, secondary colour is for the buttons and such.  
You don't have to supply contact info for every person.  
You do not have to supply a project logo.  
The example uses relative paths. Absolute ones are fine too.  

```
//frontend config
(function (window) {
  window.__env = window.__env || {};

  //this is absolutely required
  //url for backend api
  window.__env.apiUrl = 'https://api-url/'

  window.__env.logos = [
    {logo:"./style/images/alberta.png", link:"https://www.ualberta.ca/index.html"},
    {logo:"./style/images/hevga.png", link:"https://hevga.org/"}
  ]

  window.__env.people = [
    {role:"Principal Investigator" , desc:"Very important person, Digital Humanities, University of Alberta,", contact:"sean.gouglas@ualberta.ca"},
    {role:"Project Partner", desc:"Another cool person, Important job, Neat community partner", contact:""}
  ]


  window.__env.header = {
    logo: {"img":null, link:''},
    prompt:'Thank you for your interest in participating in the Cool project. Please carefully read and sign the consent form below.'
  }


  window.__env.config =  {
    //links need to be google font links
    //not the actual html tag or any of the preconnect stuff, just the link
    style: {
      background_colour:{r:255, g:255, b:255},
      text_color:{r:0, g:0, b:0},
      primary_colour: {r:41, g:170, b:226},
      secondary_colour:  {r:238, g:201, b:55},
      main_font: {name:'Roboto Condensed', link:'https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@300;400;700&display=swap'},
      emphasis_font: {name:'Oswald', link:'https://fonts.googleapis.com/css2?family=Oswald:wght@300&display=swap'}
    },
    //these need to match the ones in backend config + are the values that need to appear in the form templ
    consent_fields: [{name:"participant_name", required:true, type:'text', prompt:"Full Name:"}, {name:"participant_signature", required:true, type:'signature', prompt:'Please sign below to confirm your consent.'}],
    //if there was one of the above that was a checkbox, it would look at minimum like {name:"foo", type:"checkbox", na:false, prompt:"Do something"}
    //the only checkbox currently supported are binary (with a not applicable option)
    download_filename: "consent_signed.pdf",
    templates: {form:'views/body.html', confirm:'views/confirm.html'}

  }



}(this));

```


#### Example body HTML

HTML markup is simple and very forgiving.  
If you need to check syntax, check out the [W3S tutorials](https://www.w3schools.com/html/).  
Any specific styling beyond fonts and colours needs to be done inline in the template.  

```
<style>
  .form-part {margin-bottom: 2vh;}
  .form-title {font-size: 120%; font-weight: bold;}
  .section-title {text-decoration: underline;}
  #identifiers {
    font-size: 80%;
  }
  #form-title {
    text-align: center;
    width: 100%;
    padding: 15px;
    margin-top: 2vh;
    margin-bottom: 2vh;
  }
  </style>
<div id="custom-form">
  <div id="identifiers" class="form-part">
    <div>Cool Study</div>
    <div>Ethics approval number</div>
  </div>
  <h3 class="form-part" id="form-title">Interview Consent Form</h3>
  <div class="form-part">
    <span class="section-title">Study Title:</span>
    <span>Cool Study</span>
  </div>
  <div class="form-part">
    <div class="section-title">Background and Purpose</div>
    <div><p>Thank you for agreeing to participate in a research project on cool things. An awesome person is leading this study, which is being conducted in partnership with a friendly community partner. We plan to explore things and stuff. The report will identify stuff that we found propose important avenues for other things to look at.</p></div>
  </div>
  <div class="form-part">
    <div class="section-title">Procedures</div>
    <div><p>Participation in this stage of the study involves participating in a 30-minute interview with a member of the project team, regarding your experiences with stuff. This interview will be recorded and transcribed so we may compare your responses to those of other participants.</p></div>
  </div>
  <div class="form-part">
    <div class="section-title">Benefits and Risks</div>
    <div><p>Participation in this project is voluntary and involves no unusual risks to you. You may rescind your permission at any time with no negative consequences. You can refuse to participate or withdraw from the project at any time with no negative consequences.</p></div>
  </div>
  <div class="form-part">
    <div class="section-title">Confidentiality & Anonymity</div>
    <div>
      <p>Only the research team will have access to the information collected in this project. Your name will not appear in any reports of this research unless you explicitly grant permission to do so. You have a right to review a copy of any survey, questionnaire, checklist, etc. that is being administered.</p>
      <p>Any research assistants involved with this project will comply with the University of Alberta Standards for the Protection of Human Research Participants. Any other research personnel (e.g., transcribers) will be required to sign a confidentiality agreement that prohibits them from conveying any details about the data collected during this project to anyone other than the research team members for this project.</p>
      <p>Data will be kept for 7 years following completion of the research study and will remain in secure storage during that time. You are entitled to a copy of the final report of this study. Results from this research study may be used for research articles, presentations, and teaching purposes. For all uses, data will be handled in compliance with the University Standards. Data will be kept safe.</p>
      <p>There are several very clear rights that you are entitled to as a participant in any research conducted by a researcher from the University of Alberta. You have the right</p>
      <p>
        <ul>
          <li>To not participate;</li>
          <li>To withdraw from the interview at any time without prejudice to pre-existing entitlements, and to continuing and meaningful opportunities for deciding whether or not to continue to participate;</li>
          <li>To withdraw from the study until you can't anymore;</li>
          <li>To opt out without penalty and any collected data withdrawn from the database and not included in the study;</li>
          <li>To privacy, anonymity, and confidentiality;</li>
          <li>To safeguards for security of data (data are to be kept for a minimum of 7 years following completion of research);</li>
          <li>To disclosure of the presence of any apparent or actual conflict of interest on the part of the researcher(s); and</li>
          <li>To a copy of any final report that may be a result of the collected data.</li>
        </ul>
      </p>
    </div>
  </div>
  <div class="form-part">
    <div class="section-title">Ethics Approval Statement</div>
    <div><p>The plan for this study has been reviewed by a Research Ethics Board at the University of Alberta. If you have questions about your rights or how research should be conducted, please contact <a href="mailto:reoffice@ualberta.ca">reoffice@ualberta.ca</a>.</p></div>
  </div>
  <div class="form-part">
    <div class="section-title">Consent Statement</div>
    <div><p>I have read this form and the research study has been explained to me. I have been given the opportunity to ask questions and my questions have been answered. If I have additional questions, I have been told whom to contact. I agree to participate in the research study described above and will receive a copy of this consent form. I will receive a copy of this consent form after I sign it.</p></div>
  </div>

</div>
```

#### Example confirmation screen HTML

```
<div id="message">
  <p>Thank you for consenting to participate in <b>The First Three Years</b>!</p>
  <p>We look forward to working with you.</p>
  <div class="dot-sep"><img src="./style/images/dots.png"></div>
  <div id="interview-prompt">Have you booked your first interview? <a href="https://bit.ly/3mU6132" target="_blank">CLICK HERE</a> to schedule it!</div>
</div>

```

var env={};

if(window){
  Object.assign(env, window.__env);
}

//for scale
var vh = window.innerHeight/100;
var vw = window.innerWidth/100;




var app = angular.module('online-consent',['ngRoute', 'ngSanitize', 'ngAnimate', 'ui.bootstrap', 'signature', 'toastr']);

//to enable lodash
app.constant('_', window._)
  .run(function ($rootScope) {
     $rootScope._ = window._;
});

/*app.config(function($routeProvider) {

    //configure the routes
    $routeProvider
    .when("/", {
        templateUrl : "../views/form.html",
    })
    .when("/confirm", {
        templateUrl : "../views/confirm.html",
    })

});*/

app.config(function(toastrConfig) {
  angular.extend(toastrConfig, {
    closeButton: true
  });
});



app.controller('ctrl', function($scope, apiService, $window, $document, $uibModal, $location, $anchorScroll, $sce, $timeout, toastr) {

  //deal with adding the extra stylesheet
  let main_font = __env.config.style.main_font.name
  let emph_font= __env.config.style.emphasis_font.name
  let mf = document.createElement("link")
  mf.href = __env.config.style.main_font.link
  mf.rel = 'stylesheet'
  let ef = document.createElement("link")
  ef.href = __env.config.style.emphasis_font.link
  ef.rel = 'stylesheet'
  document.head.appendChild(mf)
  document.head.appendChild(ef)


  let bg_color = `rgb(${__env.config.style.background_colour.r}, ${__env.config.style.background_colour.g}, ${__env.config.style.background_colour.b})`
  let txt_color = `rgb(${__env.config.style.text_color.r}, ${__env.config.style.text_color.g}, ${__env.config.style.text_color.b})`
  let pr_color = `rgb(${__env.config.style.primary_colour.r}, ${__env.config.style.primary_colour.g}, ${__env.config.style.primary_colour.b})`
  let sec_color =  `rgb(${__env.config.style.secondary_colour.r}, ${__env.config.style.secondary_colour.g}, ${__env.config.style.secondary_colour.b})`
  let sec_changed =  `rgb(${(__env.config.style.secondary_colour.r -40)%255 }, ${(__env.config.style.secondary_colour.g -40)%255 }, ${(__env.config.style.secondary_colour.b-40)%255 })`
  st_str = `
  body {
    font-family: ${main_font};
    background-color: ${pr_color};
    color:${txt_color}
  }

  #loading-overlay {
    background-color: ${bg_color};
  }

  .fa-spinner {
    color: ${sec_color};
  }

  button {
    font-family: ${emph_font};
    background-color: ${sec_color};
  }

  button:hover {
    background-color:  ${sec_changed};
  }

  h1, h2, h3, h4, h5, h6 {
    font-family:  ${emph_font};
  }

  #preamble {
    font-family:  ${emph_font};
  }

  .section-title {
    font-family:  ${emph_font};
  }

  #view-content {
    background-color: ${bg_color}
  }
  `

  var styleSheet = document.createElement("style")
  styleSheet.id = "var-styles"
  styleSheet.type = "text/css"
  styleSheet.innerText = st_str
  document.head.appendChild(styleSheet)

  $scope.model = {
    consent:{},
    sendemail: false,
    complete: false,
    inProgress: false,
    istouch:  (('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (navigator.msMaxTouchPoints > 0))

  }


  //window.addEventListener('load', function () {

   $scope.model.prompt= __env.prompt
   $scope.model.logos= __env.logos
   $scope.model.people= __env.people
   $scope.model.config= __env.config



  //})

    $scope.submit_disabled = function() {
      let ret = false
      if (!$scope.model.contact) {
        return true
      }
      for(let i=0;i<$scope.model.config.consent_fields.length;i++){
        if($scope.model.config.consent_fields[i].required) {
          if(!$scope.model.consent[$scope.model.config.consent_fields[i].name]) {
            ret = true
          }
        }
      }
      return ret
    }
   //there is surely a better way to do this, but this works
   /*$scope.submit_disabled = function(){
     let ret = false
     for(let i=0;i<$scope.model.config.consent_fields.length;i++){
       if($scope.model.config.consent_fields[i].required) {
         if(!$scope.model.consent[$scope.model.config.consent_fields[i].name] || $scope.model.consent[$scope.model.config.consent_fields[i].name].length==0) {
           ret=true
         }
       }
     }
     return ret
   }*/

   //code gratefully borrowed from here: https://powerusers.microsoft.com/t5/Using-Flows/PDF-Returned-from-HTTP-Response-is-Blank/td-p/823088
   $scope.download = function(){
      var outputFileName = $scope.model.config.download_filename
      if (typeof window.chrome !== 'undefined') {
          // Chrome version
          var link = document.createElement('a');
          link.href = window.URL.createObjectURL( $scope.model.downloadData);
          link.download = outputFileName;
          link.click();
      } else if (typeof window.navigator.msSaveBlob !== 'undefined') {
          // IE version
          var blob = new Blob([ $scope.model.downloadData], { type: 'application/pdf' });
          window.navigator.msSaveBlob(blob, outputFileName);
      } else {
          // Firefox version
          var file = new File([ $scope.model.downloadData], outputFileName, { type: 'application/force-download' });
          window.open(URL.createObjectURL(file));
      }
   }

   $scope.submit = function() {
     for(let i =0;i<$scope.model.config.consent_fields.length;i++) {
       if($scope.model.config.consent_fields[i].type=='signature') {
         $scope.model.consent[$scope.model.config.consent_fields[i].name] = $scope.model.consent[$scope.model.config.consent_fields[i].name].dataUrl
       }
     }

     let can = document.getElementsByTagName('canvas')
     for(let i=0;i<can.length;i++) {
       let c = can[i].getContext('2d');
       c.clearRect(0, 0, can[i].width, can[i].height);
     }

     data = {
       consent: $scope.model.consent,
       contact: $scope.model.contact,
       sendEmail: $scope.model.sendemail
     }

     //validate email, add toast if invalid
     apiService.validate($scope.model.contact.email).then(function(d){
       err = d["error"]
       if(err) {
          toastr.error(err, "Error");
       }
        //if it is valid, send the request
       else {
         //start spinner
         $scope.model.inProgress = true
         //need better error handling
         apiService.sendData(data).then(function(form){
           //transform the response so that it can be downloaded

           $scope.model.downloadData = form;
           //navigate to confirmation page
           $scope.model.complete = true
           $scope.model.inProgress = false

           //if not going to a new page, add a toast
           if(!$scope.model.config.confirm) {
             toastr.success("Submission complete!")
           }




           if(!$scope.model.sendemail) {
             $scope.download()
           }
           $scope.model.consent = {}
           $scope.model.contact={}

         })
       }

     })


   }
})


//for interacting with an api
//this could (should) probably live in its own file...
app.service('apiService', function($http, $q) {
  return ({
   validate: validate,
   sendData: sendData
  });

  function validate(email){
    var request = $http({
      method: "post",
      url: __env.apiUrl + 'validate',
      headers: {
        'Content-Type': 'application/json'
      },
      data: {email:email}
    });
    return( request.then( handleSuccess, handleError ) );
  }

  function sendData(payload) {
          var request = $http({
            method: "post",
            url: __env.apiUrl + 'submit',
            headers: {
              'Content-Type': 'application/json',
            },
            responseType: 'blob',
            data: payload
          });
          return( request.then( handleSuccess, handleError ) );
  }

  function handleError( response ) {
    if (! angular.isObject( response.data ) ||! response.data.message) {
      return( $q.reject( "An unknown error occurred." ) );
    }
    // Otherwise, use expected error message.
    return( $q.reject( response.data.message ) );
  }

  function handleSuccess( response ) {
    return( response.data );
  }
});

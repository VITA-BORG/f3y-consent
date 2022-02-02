var env={};

if(window){
  Object.assign(env, window.__env);
}

//for scale
var vh = window.innerHeight/100;
var vw = window.innerWidth/100;




var app = angular.module('f3y-consent',['ngRoute', 'ngSanitize', 'ngAnimate', 'ui.bootstrap', 'signature', 'toastr']);

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
  $scope.model = {
    institutions:[
      {logo:"./style/images/alberta.png", link:"https://www.ualberta.ca/index.html"},
      {logo:"./style/images/western.png", link:"https://uwo.ca/"},
      {logo:"./style/images/waterloo.png", link:"https://uwaterloo.ca/"},
      {logo:"./style/images/york.png", link:"https://www.yorku.ca/glendon/"}
    ],
    people: [
      {role:"Principal Investigator" , desc:"Dr. Sean Gouglas, Professor, Digital Humanities, University of Alberta,", contact:"sean.gouglas@ualberta.ca"},
      {role:"Co-Investigator", desc:"Dr. Johanna Weststar, Associate Professor, DAN Department of Management & Organizational Studies, Western University,", contact:"weststar@uwo.ca"},
      {role:"Co-Investigator", desc:"Dr. Jennifer Whitson, Associate Professor, Stratford/Sociology and Legal Studies, University of Waterloo,", contact:"whitson@uwaterloo.ca"},
      {role:"Co-Investigator", desc:"Dr. Alison Harvey, Assistant Professor, Communications, York University (Glendon),", contact:"alison.harvey@glendon.yorku.ca"}
    ],
    consent:{},
    sendemail: false,
    complete: false,
    inProgress: false,
    istouch:  (('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (navigator.msMaxTouchPoints > 0))
  }

   $scope.$on('$locationChangeSuccess', function($event, next) {
     if(next.endsWith('confirm') && !$scope.model.complete) {
       $location.path("/")
     }
   })


   //there is surely a bettre way to do this, but this works
   $scope.submit_disabled = function(){
     return ($scope.model.istouch && !$scope.model.signature) || (!$scope.model.istouch && (!$scope.model.consent.typed ||$scope.model.consent.typed.length==0 )) || $scope.model.consent.recording == undefined || $scope.model.consent.surveys == undefined || $scope.model.consent.twitter == undefined || $scope.model.consent.linkedin == undefined || $scope.model.consent.cv == undefined || $scope.model.consent.quotations == undefined || $scope.model.consent.email == undefined  ||  $scope.model.contact.email==undefined || $scope.model.contact.email.length==0 || $scope.model.inProgress || !$scope.model.signature;
   }

   $scope.submit = function() {
     if($scope.model.signature) {
       $scope.model.consent.signature = $scope.model.signature.dataUrl
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
           //$location.path('confirm')
            $scope.model.inProgress = false
         })
       }

     })


   }

   //vode gratefully borrowed from here: https://powerusers.microsoft.com/t5/Using-Flows/PDF-Returned-from-HTTP-Response-is-Blank/td-p/823088
   $scope.download = function(){
      var outputFileName = 'F3Y_consent_signed.pdf'
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

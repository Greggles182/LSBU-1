function getStatus(){
  var xmlHTTPObject = new XMLHttpRequest();
  xmlHTTPObject.onreadystatechange = serverStatusResponse;
  xmlHTTPObject.requestType = 'STATUS'; 
  xmlHTTPObject.open("POST", "/php/getStatus.php", true);
  xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
  var sendStr = "00x93mn7sx";
  xmlHTTPObject.timeout = 5000;
  xmlHTTPObject.send(sendStr);
}

function serverStatusResponse(){
  //a readyState of 4 signifies that the data was transmitted and now a response has been recieved.
  //status = 200 signifies that the data receieved is 'OK'.
  if  (this.readyState == 4 && this.status == 200){
    request = this.requestType;
    //the responseText property contains the returned string of data from the web server.
    var responseStr = this.responseText;	
    //alert(responseStr);
    switch  (request){
      case 'STATUS':
          statusResponse(responseStr);
      break;
      default:
    }
  }
}

function statusResponse(responseStr){
  
  if (typeof lastStatusValue === 'undefined'){
    lastStatusValue = -1;
  }
  if (responseStr == lastStatusValue){
    //no status change since last request
    return;
  }else{
    lastStatusValue = responseStr;
  }
  switch (responseStr){
    case '1':
      //active
      document.getElementById('status').innerHTML = 'Active';
      var dots = document.getElementsByClassName('dots');
      for (var i=0; i < dots.length; i++){
        dots[i].className = 'dots s';	
      }
    break;
    case '2':
      //paused
      document.getElementById('status').innerHTML = 'Paused';
      var dots = document.getElementsByClassName('dots');
      for (var i=0; i < dots.length; i++){
        dots[i].className = 'dots s1';	
      }
    break;
    case '0':
      //inactive
      document.getElementById('status').innerHTML = 'Inactive';
      var dots = document.getElementsByClassName('dots');
      for (var i=0; i < dots.length; i++){
        dots[i].className = 'dots s2';	
      }
    break;
    case '3':
      //serious error (inactive)
      document.getElementById('status').innerHTML = 'Inactive';
      var dots = document.getElementsByClassName('dots');
      for (var i=0; i < dots.length; i++){
        dots[i].className = 'dots s3';	
      }
    break;
  }
}

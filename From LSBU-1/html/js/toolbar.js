function showLoader(){
  document.getElementById('loader-wrapper').style.visibility = 'visible';
}

function hideLoader(){
  document.getElementById('loader-wrapper').style.visibility = 'hidden';
}

function backupDB(){
  showLoader();
  sendConfigCommand("BACKUP");
}

function viewErrLog(){
  var win = window.open('Error_log.txt', '_blank');
  win.focus();
}

function clearErrLog(){
  showLoader();
  sendConfigCommand("CLEARERRORLOG");
}

function viewTroubleshooting(){
  window.location.href ='troubleshooting.html';
}

function sendConfigCommand(command){
  var xmlHTTPObject = new XMLHttpRequest();
  xmlHTTPObject.onreadystatechange = cfgServerResponse;
  xmlHTTPObject.requestType = command; 
  xmlHTTPObject.open("POST", "/php/troubleshooting.php", true);
  xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
  var sendStr = "command=" + command;
  xmlHTTPObject.timeout = 120000;
  xmlHTTPObject.ontimeout = cfgRequestTimeout;
  xmlHTTPObject.send(sendStr);
}

function cfgRequestTimeout(){
  hideLoader();
  alert("Request to server timed out.");
}

function cfgServerResponse(){
  //a readyState of 4 signifies that the data was transmitted and now a response has been recieved.
  //status = 200 signifies that the data receieved is 'OK'.
  if  (this.readyState == 4 && this.status == 200){
    request = this.requestType;
    //the responseText property contains the returned string of data from the web server.
    var responseStr = this.responseText;	
    //alert(responseStr);
    switch  (request){
      case 'BACKUP':
          alert(responseStr);
      break;
      case 'CLEARERRORLOG':
          alert(responseStr);
      break;
      default:
    }
    hideLoader();
  }
}

function btnConfigClick(){
  var cfgContainer = document.getElementById('configContainer');
  if (cfgContainer.style.visibility == 'visible'){
    cfgContainer.style.visibility = 'hidden';
  }else{
    cfgContainer.style.visibility = 'visible';
  }
}

function showLoader(){
  document.getElementById('loader-wrapper').style.visibility = 'visible';
}

function hideLoader(){
  document.getElementById('loader-wrapper').style.visibility = 'hidden';
}

function restoreDB(){
  showLoader();
  sendCommandPHP("RESTORE");
}

function factoryReset(){
  showLoader();
  sendCommandDB("FACTORY", "");
}

function sendCommandPHP(command){
  var xmlHTTPObject = new XMLHttpRequest();
  xmlHTTPObject.onreadystatechange = serverResponse;
  xmlHTTPObject.requestType = command; 
  xmlHTTPObject.open("POST", "/php/troubleshooting.php", true);
  xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
  var sendStr = "command=" + command;
  xmlHTTPObject.timeout = 120000;
  xmlHTTPObject.ontimeout = requestTimeout;
  xmlHTTPObject.send(sendStr);
}

function sendCommandDB(command, code){
  const currentHostname = window.location.hostname;
  var xmlHTTPObject = new XMLHttpRequest();
  xmlHTTPObject.onreadystatechange = serverResponse;
  xmlHTTPObject.requestType = command; 
  xmlHTTPObject.open("POST", `http://${currentHostname}:3440/`, true);
  xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
  var sendStr = "command=" + command + "&code=" + code;
  xmlHTTPObject.timeout = 30000;
  xmlHTTPObject.ontimeout = requestTimeout;
  xmlHTTPObject.send(sendStr);
}

function requestTimeout(){
  hideLoader();
  alert("Request to server timed out.");
}

function serverResponse(){
  //a readyState of 4 signifies that the data was transmitted and now a response has been recieved.
  //status = 200 signifies that the data receieved is 'OK'.
  if  (this.readyState == 4 && this.status == 200){
    request = this.requestType;
    //the responseText property contains the returned string of data from the web server.
    var responseStr = this.responseText;	
    //alert(responseStr);
    switch  (request){
      case 'FACTORY':
          alert(responseStr);
      break;
      case 'RESTORE':
          alert(responseStr);
      break;
      default:
    }
    hideLoader();
  }
}

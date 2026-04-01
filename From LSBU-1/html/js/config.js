function getConfig(){
  showLoader();
  sendCommand("GETCONFIG", "");
}	

function setConfig(){
  var sessionName = document.getElementById('sessionNameText').value;
  var tosend = sessionName + "<P0>";
  //sendCommand("SETCONFIG", document.getElementById('text1').value);
  var table = document.getElementById('tbody');
  var nextRow = table.firstElementChild;
  
  while (nextRow !== null){
    if (validateRow(nextRow) == 0){
      if (tosend != sessionName + "<P0>"){
        tosend += "<P1>";
      }
      for (var i=0; i < nextRow.children.length; i++){
        if (i == 0){
          tosend += nextRow.children[i].tag;
        }else{
          tosend += "<P2>" + nextRow.children[i].innerHTML;
        }
      }
    }else{
      alert("Logger not started. Invalid entry for channel with slave address " + nextRow.children[1].innerHTML + " ,channel address " + nextRow.children[2].innerHTML);
      return;
    }
    nextRow = nextRow.nextElementSibling;
  }
  if (checkIntervalsValid() == false){
    alert("Conflicting intervals identified. Please specify one interval to be used.");
    return;
  }
  showLoader();
  sendCommand("SETCONFIG", tosend);
}	

function validateRow(row){
  if (row.children[0].tag == "1"){ 	//if not 1, not enabled - cant be invalid data entry.
    //series of validation steps, if any fail, return -1 early, if reaches end, return 0.
    if (row.children[3].innerHTML.length == 0){ return -1;}
    if (row.children[4].innerHTML.length == 0){ return -1;}
    if (row.children[5].innerHTML.length == 0){ return -1;}
    if (row.children[6].innerHTML.length == 0){ return -1;}
    if (row.children[7].innerHTML.length == 0){ return -1;}
    if (isNumeric(row.children[5].innerHTML) == false){ return -1;}
    if (row.children[5].innerHTML > 2147483647 || row.children[5].innerHTML < 1){ return -1;}
    if (isNumeric(row.children[6].innerHTML) == false){ return -1;}
    if (isNumeric(row.children[7].innerHTML) == false){ return -1;}
  }
  //reached here, must be valid.
  return 0;
}

function checkIntervalsValid(){
  var table = document.getElementById('tbody');
  var nextRow = table.firstElementChild;
  if (nextRow === null){
    return true;
  }
  var interval = nextRow.children[5].innerHTML;
  while (nextRow !== null){
    if (nextRow.children[5].innerHTML !== interval){
      return false;
    }
    nextRow = nextRow.nextElementSibling;
  }
  //if reaches here, no different intervals - return true.
  return true;
}

function isNumeric(n) {
  return !isNaN(parseFloat(n)) && isFinite(n); 	//from stackoverflow
}

function start(){
  var sessionName = document.getElementById('sessionNameText').value;
  var tosend = sessionName + "<P0>";
  //sendCommand("SETCONFIG", document.getElementById('text1').value);
  var table = document.getElementById('tbody');
  var nextRow = table.firstElementChild;
  
  while (nextRow !== null){
    if (validateRow(nextRow) == 0){
      if (tosend != sessionName + "<P0>"){
        tosend += "<P1>";
      }
      for (var i=0; i < nextRow.children.length; i++){
        if (i == 0){
          tosend += nextRow.children[i].tag;
        }else{
          tosend += "<P2>" + nextRow.children[i].innerHTML;
        }
      }
    }else{
      alert("Logger not started. Invalid entry for channel with slave address " + nextRow.children[1].innerHTML + " ,channel address " + nextRow.children[2].innerHTML);
      return;
    }
    nextRow = nextRow.nextElementSibling;
  }
  if (checkIntervalsValid() == false){
    alert("Conflicting intervals identified. Please specify one interval to be used.");
    return;
  }
  alert(tosend);
  showLoader();
  sendCommand("SETCONFIGSTART", tosend);
}	

function pause(){
  sendCommand("PAUSE", "")
}	
function resume(){
  sendCommand("RESUME", "");
}	
function stop(){
  sendCommand("STOP", "");
}	

function sendCommand(command, code){
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

function getStatus(){
  var xmlHTTPObject = new XMLHttpRequest();
  xmlHTTPObject.onreadystatechange = serverResponse;
  xmlHTTPObject.requestType = 'STATUS'; 
  xmlHTTPObject.open("POST", "/php/getStatus.php", true);
  xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
  var sendStr = "00x93mn7sx";
  xmlHTTPObject.timeout = 5000;
  xmlHTTPObject.send(sendStr);
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
      case 'STATUS':
          statusResponse(responseStr);
      break;
      case 'GETCONFIG':
          getConfigResponse(responseStr);
          hideLoader();
      break;
      case 'SETCONFIG':
          hideLoader();
          if (responseStr == "SUCCESS"){
            alert("Data logger set successfully.");
          }else{
            alert(responseStr);
          }
      break;
      case 'SETCONFIGSTART':
          hideLoader();
          if (responseStr == "SUCCESS"){
            getStatus();
          }else{
            alert(responseStr);
          }
      break;
      case 'PAUSE':
          if (responseStr == "SUCCESS"){
            getStatus();
          }else{
            alert(responseStr);
          }
      break;
      case 'RESUME':
          if (responseStr == "SUCCESS"){
            getStatus();
          }else{
            alert(responseStr);
          }
      break;
      case 'STOP':
          if (responseStr == "SUCCESS"){
            //return to home page.
            window.location.href = 'index.html';
          }else{
            alert(responseStr);
          }
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
      document.getElementById('containerStopped').style.visibility = 'hidden';
      document.getElementById('containerRunning').style.visibility = 'visible';
      document.getElementById('status').innerHTML = 'Active';
      document.getElementById('btnPause').innerHTML = 'Pause';
      var dots = document.getElementsByClassName('dots');
      for (var i=0; i < dots.length; i++){
        dots[i].className = 'dots s';	
      }
    break;
    case '2':
      //paused
      document.getElementById('containerStopped').style.visibility = 'hidden';
      document.getElementById('containerRunning').style.visibility = 'visible';
      document.getElementById('status').innerHTML = 'Paused';
      document.getElementById('btnPause').innerHTML = 'Resume';
      var dots = document.getElementsByClassName('dots');
      for (var i=0; i < dots.length; i++){
        dots[i].className = 'dots s1';	
      }
    break;
    case '0':
      //inactive
      document.getElementById('containerRunning').style.visibility = 'hidden';
      document.getElementById('containerStopped').style.visibility = 'visible';
      document.getElementById('status').innerHTML = 'Inactive';
      var dots = document.getElementsByClassName('dots');
      for (var i=0; i < dots.length; i++){
        dots[i].className = 'dots s2';	
      }
      getConfig();
    break;
    case '3':
      //serious error (inactive)
      document.getElementById('containerRunning').style.visibility = 'hidden';
      document.getElementById('containerStopped').style.visibility = 'visible';
      document.getElementById('status').innerHTML = 'Inactive';
      var dots = document.getElementsByClassName('dots');
      for (var i=0; i < dots.length; i++){
        dots[i].className = 'dots s3';	
      }
      getConfig();
    break;
  }
}

function getConfigResponse(responseStr){
  try{
    var splitResponse = responseStr.split("<P0>");
    if (typeof splitResponse[1] === 'undefined'){   //will be if error message returned - show error message.
      alert(responseStr);
      return;
    }
    var sessionName = splitResponse[0];
    document.getElementById('sessionNameText').value = sessionName;
    var dataStr = splitResponse[1];
    //take response from server - channels delimited by <P1>, properties of each channel delimited by <P2>
    //and load into table.
    //Once complete, dataTable it.
    
    //first delete current contents of table.
    var tbody = document.getElementById('tbody');
    tbody.innerHTML = "";
    document.getElementById('searchText').value = "";
    
    if (dataStr.length == 0){
      alert("No channels connected.");
      return;
    }
    var channelStrings = dataStr.split("<P1>");
    //for each channel.
    for (var i=0; i < channelStrings.length; i++){
      var tr = document.createElement('tr');
      //for each property.
      var properties = channelStrings[i].split("<P2>");
      for (var j=0; j < properties.length; j++){
        var td = document.createElement('td');
        var tdText = {};
        td.index = j;
        if (j==0){
          td.tag = properties[j];
          var div = document.createElement('div');
          //setting picture properties:
          div.className = 'enabled';
          if (properties[j] == 1){
            div.style.backgroundImage = "url('/images/enabled.png')";
          }else{
            div.style.backgroundImage = "url('/images/disabled.png')";
          }
          td.appendChild(div);
          td.onclick = enabledEdit;
        }else if (j<=2){
          //assign as properties come in.
          tdText = document.createTextNode(properties[j]);
          td.appendChild(tdText);
          td.style.backgroundColor = '#C0C0C0';
          td.style.cursor = 'default';
        }else if (j==3){
          //assign as properties come in.
          tdText = document.createTextNode(properties[j]);
          td.appendChild(tdText);
          td.onclick = textEdit;
          td.maxLength = 18;
        }else if(j==4){
          tdText = document.createTextNode(properties[4]);
          td.appendChild(tdText);
          td.onclick = comboEdit;
        }else{
          //everything after assign as come in but +1 due to above discrepancy.
          tdText = document.createTextNode(properties[j]);
          td.appendChild(tdText);
          td.onclick = textEdit;	
          if (j==5 || j==6 || j==7){td.maxLength = 10;}
          if (j==8){td.maxLength = 5;}
        }			
        tr.appendChild(td);
      }
      //append row to table body.
      tbody.appendChild(tr);
    }
    //table should now be populated.
    //update text displaying number of channels enabled in table.
    countChannels();
  }catch(err){
    alert("Error in the transmission format from the server.");
  }
}

function btnPauseClick(){
  if (document.getElementById('btnPause').innerHTML == "Pause"){
    pause();
  }else{
    resume();
  }
}

function setAllIntervals(interval){
  var table = document.getElementById('tbody');
  var nextRow = table.firstElementChild;
  while (nextRow !== null){
    nextRow.children[5].innerHTML = interval;
    nextRow = nextRow.nextElementSibling;
  }
}

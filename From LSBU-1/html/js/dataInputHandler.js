function btnNew(){
  channelsLoaded = false;
  resetMenu();
  resetTabDropdown();
  resetForm();
  var button = document.getElementById('btnType');
  button.style.visibility = 'visible';
  btnTypeClick();
}

function resetMenu(){
  var button = document.getElementById('btnType');
  button.className = 'vertToolbarButton';
  button.style.borderRight = '3px solid #2e2e2e';
  button.style.top = '60px';
  button.style.left = '0px';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnRange');
  button.className = 'vertToolbarButton';
  button.style.borderRight = '3px solid #2e2e2e';
  button.style.top = '120px';
  button.style.left = '0px';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnChannels');
  button.className = 'vertToolbarButton';
  button.style.borderRight = '3px solid #2e2e2e';
  button.style.top = '180px';
  button.style.left = '0px';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnSettings');
  button.className = 'vertToolbarButton';
  button.style.borderRight = '3px solid #2e2e2e';
  button.style.top = '240px';
  button.style.left = '0px';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnGenerate');
  button.style.visibility = 'hidden';
  button.className = 'formButton';
  var subtext = document.getElementById('typeText');
  subtext.innerHTML = "";
  var subtext = document.getElementById('rangeText');
  subtext.innerHTML = "";
  var subtext = document.getElementById('channelsText');
  subtext.innerHTML = "";
  var subtext = document.getElementById('settingsText');
  subtext.innerHTML = "";
}

function resetTabDropdown(){
  var button = document.getElementById('btnOptions');
  button.className = 'vertToolbarButton';
  button.style.borderRight = '3px solid #2e2e2e';
  button.style.top = '60px';
  button.style.left = '0px';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnExport');
  button.className = 'vertToolbarButton';
  button.style.borderRight = '3px solid #2e2e2e';
  button.style.top = '120px';
  button.style.left = '0px';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnDelete');
  button.className = 'vertToolbarButton';
  button.style.borderRight = '3px solid #2e2e2e';
  button.style.top = '180px';
  button.style.left = '0px';
  button.style.visibility = 'hidden';
}

function clearForm(){
  var button = document.getElementById('btnChart');
  button.className = 'formButton';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnCSV');
  button.className = 'formButton';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnRangeDone');
  button.className = 'formButton';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnChannelsDone');
  button.className = 'formButton';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnSettingsDone');
  button.className = 'formButton';
  button.style.visibility = 'hidden';
  var button = document.getElementById('btnOptionsDone');
  button.className = 'formButton';
  button.style.visibility = 'hidden';
  var table= document.getElementById('sessionTable');
  table.style.visibility = 'hidden';
  var table= document.getElementById('channelTable');
  table.style.visibility = 'hidden';	
  var table= document.getElementById('settingsTable');
  table.style.visibility = 'hidden';	
  var table= document.getElementById('optionsTable');
  table.style.visibility = 'hidden';	
  var label= document.getElementById('errorLabel');
  label.style.visibility = 'hidden';	
  var label= document.getElementById('channelLabel');
  label.style.visibility = 'hidden';	
}
function resetForm(){
  var button = document.getElementById('btnChart');
  button.removeAttribute("style");
  button.className = 'formButton';
  var button = document.getElementById('btnCSV');
  button.removeAttribute("style");
  button.className = 'formButton';
  var button = document.getElementById('btnRangeDone');
  button.removeAttribute("style");
  button.className = 'formButton';
  var button = document.getElementById('btnChannelsDone');
  button.removeAttribute("style");
  button.className = 'formButton';
  var button = document.getElementById('btnSettingsDone');
  button.removeAttribute("style");
  button.className = 'formButton';
  var button = document.getElementById('btnOptionsDone');
  button.removeAttribute("style");
  button.className = 'formButton';
  var table= document.getElementById('sessionTable');
  table.style.visibility = 'hidden';
  var table= document.getElementById('channelTable');
  table.style.visibility = 'hidden';	
  var table= document.getElementById('settingsTable');
  table.style.visibility = 'hidden';
  var table= document.getElementById('optionsTable');
  table.style.visibility = 'hidden';	
  var label= document.getElementById('channelLabel');
  label.style.visibility = 'hidden';	
  var label= document.getElementById('errorLabel');
  label.style.visibility = 'hidden';	
  document.getElementById('settingsName').value = "";
  document.getElementById('calibrationCheckbox').checked = false;
  document.getElementById('liveCheck').checked = false;
  document.getElementById('intervalList').value = "default";
}

function clearChart(){
  if (typeof scatterChart !== 'undefined'){
    scatterChart.clear();
    document.getElementById('chartCanvas').style.visibility = 'hidden';
  }
  document.getElementById('legendDiv').style.visibility = 'hidden';
}

function resetBorders(){
  var button = document.getElementById('btnType');
  button.style.borderRight = '3px solid #2e2e2e';
  var button = document.getElementById('btnRange');
  button.style.borderRight = '3px solid #2e2e2e';
  var button = document.getElementById('btnChannels');
  button.style.borderRight = '3px solid #2e2e2e';
  var button = document.getElementById('btnSettings');
  button.style.borderRight = '3px solid #2e2e2e';
  var button = document.getElementById('btnOptions');
  button.style.borderRight = '3px solid #2e2e2e';
}

function btnTypeClick(){
  resetBorders();
  clearForm();
  var button = document.getElementById('btnType');
  button.style.borderRight = '3px solid #232323';
  button.style.visibility = 'visible';
  setTimeout(function (){			
    var button = document.getElementById('btnChart');
    button.style.visibility = 'visible';
    if (animations == true){
      button.className += ' chartOut';
    }else{
      button.className += ' nchartOut';
    }
    var button = document.getElementById('btnCSV');
    button.style.visibility = 'visible';
    if (animations == true){
      button.className += ' csvOut';
    }else{
      button.className += ' ncsvOut';
    }
  }, 0);
//must encorporate the timeout function otherwise the compiler adds the classes together and no animation rehappens.
}

function btnChartClick(){
  dataType = "Chart";
  document.getElementById('btnChart').style.backgroundColor = 'lime';
  document.getElementById('btnCSV').style.backgroundColor = 'white';
  document.getElementById('typeText').innerHTML = "Chart";
  if (btnRange.style.visibility == 'hidden'){
    document.getElementById('btnRange').style.visibility = 'visible';
    btnRangeClick();
  }else{
    resetBorders();
    clearForm();
  }
}
function btnCSVClick(){
  dataType = "CSV";
  document.getElementById('btnChart').style.backgroundColor = 'white';
  document.getElementById('btnCSV').style.backgroundColor = 'lime';
  document.getElementById('typeText').innerHTML = "CSV";
  if (btnRange.style.visibility == 'hidden'){
    document.getElementById('btnRange').style.visibility = 'visible';
    btnRangeClick();
  }else{
    resetBorders();
    clearForm();
  }
}

function btnRangeClick(){
  resetBorders();
  clearForm();
  var button = document.getElementById('btnRange');
  button.style.borderRight = '3px solid #232323';
  button.style.visibility = 'visible';
  document.getElementById('sessionTable').style.visibility = 'visible';
  setTimeout(function (){
    var button = document.getElementById('btnRangeDone');
    button.style.visibility = 'visible';
    if (animations == true){
      button.className += ' rangeDoneOut';
    }else{
      button.className += ' nrangeDoneOut';
    }
  }, 0);
  loadSessions();
}

function btnRangeDoneClick(){
  var nextRow = document.getElementById('sessionBody').firstElementChild;
  var isSelection = false;
  while (nextRow !== null){
    if (nextRow.style.backgroundColor == 'lime'){
      var isSelection = true;
      document.getElementById('rangeText').innerHTML = nextRow.children[1].innerHTML;
    }
    nextRow = nextRow.nextElementSibling;
  }
  if (isSelection == false){
    document.getElementById('errorLabel').innerHTML = "No range selected.";
    document.getElementById('errorLabel').style.visibility = 'visible';
    return;
  }
  channelsLoaded = false;
  btnChannelsClick();
}

function btnChannelsDoneClick(){
  document.getElementById('channelsText').innerHTML = document.getElementById('channelLabel').innerHTML.split(": ")[1];
  if (btnSettings.style.visibility == 'hidden'){
    btnSettingsClick();
  }else{
    resetBorders();
    clearForm();	
  }
}

function btnChannelsClick(){
  resetBorders();
  clearForm();
  var button = document.getElementById('btnChannels');
  button.style.borderRight = '3px solid #232323';
  button.style.visibility = 'visible';	
  setTimeout(function (){
    var button = document.getElementById('btnChannelsDone');
    button.style.visibility = 'visible';
    if (animations == true){
      button.className += ' channelsDoneOut';
    }else{
      button.className += ' nchannelsDoneOut';
    }
  }, 0);
  if (channelsLoaded== false){
    channelRequestWrapper();
  }
  var table = document.getElementById('channelTable');
  table.style.visibility = 'visible';
  var label= document.getElementById('channelLabel');
  label.style.visibility = 'visible';	
  channelsLoaded = true;
}

function btnSettingsClick(){
  resetBorders();
  clearForm();
  var button = document.getElementById('btnSettings');
  button.style.borderRight = '3px solid #232323';
  button.style.visibility = 'visible';
  setTimeout(function (){			
    var button = document.getElementById('btnSettingsDone');
    button.style.visibility = 'visible';
    if (animations == true){
      button.className += ' settingsDoneOut';
    }else{
      button.className += ' nsettingsDoneOut';
    }
  }, 0);
  document.getElementById('settingsTable').style.visibility = 'visible';
}
function btnSettingsDoneClick(){
  updateSettingsString();
  resetBorders();
  clearForm();
  setTimeout(function (){			
    var button = document.getElementById('btnGenerate');
    button.style.visibility = 'visible';
    if (animations == true){
      button.className += ' generateOut';
    }else{
      button.className += ' ngenerateOut';
    }
  }, 0);
}

function btnGenerateClick(){
  if (document.getElementById('typeText').innerHTML == 'Chart'){
    //no verification is necessary since generate button will only show once data has been filled, and it cannot be unfilled.
    addTab();
  }else{
    exportCSV();
  }
}

function exportCSV(){
  //need to make a export tab so request wrapper can use same functionality as when producing a chart tab.
  var tab = {};
  tab.type = document.getElementById('typeText').innerHTML;	
  tab.requestType = "session";
  //finding sessionID
  var nextRow = document.getElementById('sessionBody').firstElementChild;
  while (nextRow !== null){
    if (nextRow.style.backgroundColor == 'lime'){
      tab.sessionID = nextRow.children[0].innerHTML;
    }
    nextRow = nextRow.nextElementSibling;
  }
  tab.startTime = 'NULL';
  tab.endTime = 'NULL';
  tab.channelString = getChannelString();
  tab.calibrations = document.getElementById('calibrationCheckbox').checked;
  tab.interval = document.getElementById('intervalList').value;
  requestWrapper(tab);
}

function addTab(){
  if (typeof numTabs === 'undefined'){
    //i.e. first tab
    numTabs = 1;
  }else{
    numTabs++;
  }
  changeToolbarDestination();
  var button = document.getElementById('btnType');
  if (animations == true){
      button.className += ' typeUp';
    }else{
      button.style.visibility = 'hidden';
  }
  var button = document.getElementById('btnRange');
  if (animations == true){
      button.className += ' rangeUp';
    }else{
      button.style.visibility = 'hidden';
  }
  var button = document.getElementById('btnChannels');
  if (animations == true){
      button.className += ' channelsUp';
    }else{
      button.style.visibility = 'hidden';
  }
  var button = document.getElementById('btnSettings');
  if (animations == true){
      button.className += ' settingsUp';
    }else{
      button.style.visibility = 'hidden';
  }
  var button = document.getElementById('btnGenerate');
  if (animations == true){
      button.className += ' generateUp';
    }else{
      button.style.visibility = 'hidden';
  }
  var newTab = document.createElement('div');
  newTab.className = "horizToolbarButton";
  var tabText = document.createElement('div');
  tabText.className = "horizmainText";
  var settingsName = document.getElementById('settingsName').value;
  if (settingsName == ""){
    tabText.innerHTML = document.getElementById('rangeText').innerHTML;
  }else{
    tabText.innerHTML = settingsName;
  }
  newTab.appendChild(tabText);
  //global var tabLeft which indicates position from left to add the new tab.
  var tabLeft = (numTabs * 150) + 50;
  document.getElementById('upperToolbar').appendChild(newTab);
  newTab.style.top = '0px';
  newTab.style.left = tabLeft + 'px';
  newTab.onclick = tabClick;
  newTab.style.visibility = 'visible';
  
  //each tab has the following custom-defined properties: tabNumber, id, type, requestType, sessionID, startTime, endTime, channelString, calibrations, interval, liveUpdates, tabData.
  newTab.tabData = {};
  newTab.tabNumber = numTabs;
  newTab.id = "tab" + numTabs;
  newTab.type = document.getElementById('typeText').innerHTML;
  
  newTab.requestType = "session";
  //finding sessionID
  var nextRow = document.getElementById('sessionBody').firstElementChild;
  while (nextRow !== null){
    if (nextRow.style.backgroundColor == 'lime'){
      newTab.sessionID = nextRow.children[0].innerHTML;
    }
    nextRow = nextRow.nextElementSibling;
  }
  newTab.startTime = 'NULL';
  newTab.endTime = 'NULL';
  newTab.yMax = "";
  newTab.yMin = "";
  newTab.channelString = getChannelString();
  newTab.calibrations = document.getElementById('calibrationCheckbox').checked;
  newTab.interval = document.getElementById('intervalList').value;
  newTab.liveUpdates = document.getElementById('liveCheck').checked;
 
  if (typeof liveUpdatesIntervalID !== 'undefined'){
    clearInterval(liveUpdatesIntervalID );
  }
  
  activeTab = newTab;
  requestWrapper(newTab);
  
  var button = document.getElementById('btnOptions');
  button.className = "vertToolbarButton";
  button.style.visibility = 'visible';
  var button = document.getElementById('btnExport');
  button.className = "vertToolbarButton";
  button.style.visibility = 'visible';
  var button = document.getElementById('btnDelete');
  button.className = "vertToolbarButton";
  button.style.visibility = 'visible';
}

function tabClick(){
  if (activeTab.tabNumber != this.tabNumber){
    showLoader();
    var button = document.getElementById('btnOptions');
    button.className = "vertToolbarButton";
    var button = document.getElementById('btnExport');
    button.className = "vertToolbarButton";
    var button = document.getElementById('btnDelete');
    button.className = "vertToolbarButton";
    
    changeTabAnimation(this);
    setTimeout(function (){			
      var button = document.getElementById('btnOptions');
      if (animations == true){
        button.className += ' optionsDown';
      }else{
        button.className += ' noptionsDown';
      }
      button.style.visibility = 'visible';
      var button = document.getElementById('btnExport');
      if (animations == true){
        button.className += ' exportDown';
      }else{
        button.className += ' nexportDown';
      }
      button.style.visibility = 'visible';
      var button = document.getElementById('btnDelete');
      if (animations == true){
        button.className += ' deleteDown';
      }else{
        button.className += ' ndeleteDown';
      }
      button.style.visibility = 'visible';
    }, 0);
    if (typeof liveUpdatesIntervalID !== 'undefined'){
    clearInterval(liveUpdatesIntervalID );
    }
    populateChart(this.tabData);
    document.getElementById('errMessage').innerHTML = this.errMessage;
    activeTab = this;
    if (activeTab.liveUpdates == true){
      var interval = getDataInterval(activeTab);
      liveUpdatesIntervalID = setInterval(sendUpdateRequest, interval, activeTab);
    }
    hideLoader();
  }else{
    resetMenu();
    resetForm();
    document.getElementById('btnOptions').style.visibility = 'visible';
    document.getElementById('btnExport').style.visibility = 'visible';
    document.getElementById('btnDelete').style.visibility = 'visible';
  }
}

function btnDeleteClick(){
  tabDelete(activeTab);
}

function tabDelete(tab){
  //1. shifting all html tabs above tab down one.
  shiftTabs(tab.tabNumber + 1);
  for (var i=tab.tabNumber + 1; i <= numTabs; i++){
    var tempTab = document.getElementById('tab' + i);
    if (tempTab !== null){
      tempTab.tabNumber--;
      tempTab.id = "tab" + tempTab.tabNumber;
    }
  }
  //2.resetting the left menu, chart and any form buttons, clearing live updates if exist.
  resetMenu();
  resetTabDropdown();
  document.getElementById('errMessage').innerHTML = "";
  resetForm();
  clearChart();
  //3. decrement the global tabNumber and set activeTab to null so others respond to clicks, and deleting the current tab.
  numTabs--;
  if (typeof liveUpdatesIntervalID !== 'undefined'){
    clearInterval(liveUpdatesIntervalID );
  }
  activeTab.tabNumber = null;
  tab.parentElement.removeChild(tab);
}

//the following functions are used to change the animation that appears when a tab is clicked.
function findKeyframesRule(rule){
  // gather all stylesheets into an array
  var ss = document.styleSheets;
  
  // loop through the stylesheets
  for (var i = 0; i < ss.length; ++i) {
    // loop through all the rules
    for (var j = 0; j < ss[i].cssRules.length; ++j) {
      
      // find the -webkit-keyframe rule whose name matches our passed over parameter and return that rule
      if (ss[i].cssRules[j].type == window.CSSRule.KEYFRAMES_RULE && ss[i].cssRules[j].name == rule)
        return ss[i].cssRules[j];
    }
  }
  // rule not found
  return null;
}

// remove old keyframes and add new ones
function changeTabAnimation(tab){	
  for (var i=0; i <3; i++){
    if (i==0){var animation = "optionsDown";}
    if (i==1){var animation = "exportDown";}
    if (i==2){var animation = "deleteDown";}
    
    // find our keyframe rule
    var keyframes = findKeyframesRule(animation);
    if (keyframes === null){
      continue;
    }
    
    keyframes.deleteRule("0%");
    keyframes.deleteRule("70%");
    var amountLeft = 200 + parseInt(tab.style.left);
    var newRule = "0%  {left:" + amountLeft + "px; top:0px; width:147px;}";
    try{
      keyframes.insertRule(newRule);
    }catch(e){
    }
    var amountTop = 60 * (i+1);
    var newRule = "70%  {left:" + amountLeft + "px; top:" + amountTop + "px; width:147px;}";
    try{
      keyframes.insertRule(newRule);
    }catch(e){
    }
  }
}

function changeToolbarDestination(){
  for (var i=0; i <5; i++){
    if (i==0){var animation = "typeUp";}
    if (i==1){var animation = "rangeUp";}
    if (i==2){var animation = "channelsUp";}
    if (i==3){var animation = "settingsUp";}
    if (i==4){var animation = "generateUp";}
    
    // find our keyframe rule
    var keyframes = findKeyframesRule(animation);
    if (keyframes === null){
      continue;
    }
    
    keyframes.deleteRule("100%");
    var amountLeft = (numTabs * 150) + 50;
    var newRule = "100%  {left:" + amountLeft + "px; top:0px; width:147px;}";
    try{
      keyframes.insertRule(newRule);
    }catch(e){
    }
  }
}

function shiftTabs(firstNum){
  for(var i=firstNum; i<= numTabs; i++){
    var tab = document.getElementById('tab' + i);
    newLeft = parseInt(tab.style.left) - 150;
    newLeft+="px";
    tab.style.left = newLeft;
  }
}

function btnOptionsClick(){
  resetBorders();
  clearForm();
  var button = document.getElementById('btnOptions');
  button.style.borderRight = '3px solid #232323';
  button.style.visibility = 'visible';
  document.getElementById('optionsName').value = activeTab.children[0].innerHTML;
  document.getElementById('optionsIntervalList').value = activeTab.interval;
  document.getElementById('optionsCalibrationCheckbox').checked= activeTab.calibrations;
  document.getElementById('optionsLiveCheck').checked= activeTab.liveUpdates;
  document.getElementById('ymax').value = activeTab.yMax;
  document.getElementById('ymin').value = activeTab.yMin;
  setTimeout(function (){			
    var button = document.getElementById('btnOptionsDone');
    button.style.visibility = 'visible';
    if (animations == true){
        button.className += ' optionsDoneOut';
      }else{
        button.className += ' noptionsDoneOut';
    }
  }, 0);
  document.getElementById('optionsTable').style.visibility = 'visible';
}	

function btnExportClick(){
  exportDataObject(activeTab.tabData, true);
}

function btnOptionsDoneClick(){
  //if interval changed: reload the graph with new values.
  if (document.getElementById('optionsIntervalList').value != activeTab.interval){
    saveOptions();
    requestWrapper(activeTab);
    clearForm();
    resetBorders();
    return;
  }
  var ymax = document.getElementById('ymax').value;
  var ymin = document.getElementById('ymin').value;
  if ((ymax != activeTab.yMax && ymax != "") || (ymin != activeTab.yMin && ymin != "")){
    //scale changed.
    saveOptions();
    clearChart();
    populateChart(activeTab.tabData);
    clearForm();
    resetBorders();
    return;
  }
  
  if (document.getElementById('optionsCalibrationCheckbox').checked != activeTab.calibrations){
    //calibrations changed
    showLoader();
    if (document.getElementById('optionsCalibrationCheckbox').checked == true){
      applyCalibrations(activeTab.tabData);
    }else{
      removeCalibrations(activeTab.tabData);
    }
    hideLoader();
  }
  if (document.getElementById('optionsLiveCheck').checked != activeTab.liveUpdates){
    //liveupdates changed.
    //enable live updates if set:
    if (document.getElementById('optionsLiveCheck').checked == true){
      var interval = getDataInterval(activeTab);
      liveUpdatesIntervalID = setInterval(sendUpdateRequest, interval, activeTab);
    }else{
      //liveupdates been unchecked.
      clearInterval(liveUpdatesIntervalID);
    }
  }
  saveOptions();
  clearForm();
  resetBorders();
}

function saveOptions(){
  activeTab.children[0].innerHTML = document.getElementById('optionsName').value;
  activeTab.interval = document.getElementById('optionsIntervalList').value;
  activeTab.calibrations = document.getElementById('optionsCalibrationCheckbox').checked;
  activeTab.liveUpdates = document.getElementById('optionsLiveCheck').checked;
  activeTab.yMax = document.getElementById('ymax').value;
  activeTab.yMin = document.getElementById('ymin').value;
}

/*Deprecated: function timeScaleChange(){
  var startTime = document.getElementById('startTime').value;
    if (startTime == ""){
      startTime = "ALL";
    }
    var endTime = document.getElementById('endTime').value;
    if (endTime == ""){
      endTime = "NOW";
    }
    document.getElementById('rangeText').innerHTML = startTime + " to " + endTime;
}*/

function updateSettingsString(){
  var settingsstring = "";
  if  (document.getElementById('calibrationCheckbox').checked == true){
    settingsstring += "Cals: yes, ";
  }else{
    settingsstring += "Cals: no, ";
  }
  if  (document.getElementById('liveCheck').checked == true){
    settingsstring += "updates: yes, ";
  }else{
    settingsstring += "updates: no, ";
  }
  settingsstring += "interval: " + document.getElementById('intervalList').value;
  document.getElementById('settingsText').innerHTML = settingsstring;
}

function applyScale(chartData, ymax, ymin, options){
  if (ymax == "" && ymin == ""){
    //no scale set.
    return;
  }
  if (ymax == ""){
    ymax = getYmax(chartData);
  }
  if (ymin == ""){
    ymin = getYmin(chartData);
  }		
  var numSteps = 10;
  var stepWidth = (ymax - ymin) / numSteps;
  options.scaleOverride = true;
  options.scaleSteps = numSteps;
  options.scaleStartValue = Number(ymin);
  options.scaleStepWidth = stepWidth;
}

function showLoader(){
  document.getElementById('loader-wrapper').style.visibility = 'visible';
}
function hideLoader(){
  document.getElementById('loader-wrapper').style.visibility = 'hidden';
}

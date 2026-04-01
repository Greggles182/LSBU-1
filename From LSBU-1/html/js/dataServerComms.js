	//3 global variables are used in this webpage:
	//1. Loggers - an array of 5 loggerData objects, which contain the data of the current session
	//2. chartData - the array of dataSet objects used to contain data and formatting which the chart utilises.
	//3. globSessionID - the sessionID of the current session.
	
	//Class definitions
	//There is 1 main custom classes used on this webpage - dataSet
	//chartDataObject holds information about the data to be displayed on the chart and the chart formatting.
	
	//dataSet constructor function
	function dataSet(){
		//label contains channel name that will be displayed with dataset on graph.
		this.label = "";
		//stroke color - line color
		this.strokeColor = "";
		this.pointColor = "";
		//data is an array of point objects.
		//each point in data has 2 properties, x and y, and an optional 3rd, r. 
		this.data = [];
		//logger stores name of logger that the dataset came from.
		this.logger = "";	
		this.name = "";
		this.calibrations = false;
		this.offset = 0;
		this.slope = 0;
	}
	
	//This function is called whenever a new chart is to be displayed, it requests data from the web server,
	//which it needs to populate the chart.
	//It takes the sessionID of the data session to display.
	//If a value of 0 is passed as the sessionID, the function displays the latest session.
	
	function sendDataRequest(requestType, sessionID, startTime, endTime, interval, calibrations, exportOnly, channelString){	
		//Function overview: sends request to php webpage on server, which in turn communicates with database.
		//Requested data is returned in a string from the server, which is then parsed and
		//the chart data is loaded into the array of objects 'Loggers'. See help file for 'Loggers' structure.

		//When communicating with a php web server, there are 2 common ways to send data.
		//1. Websockets 2. Representational state transfer (REST)
		//I have used REST via XMLHttpRequest objects as it is simpler to program.
		
		//First a request object is instantiated.
		var xmlHTTPObject = new XMLHttpRequest();
	
		//There are 5 states that the object will pass through during the request of data from a server, 
		//representing the state of data transmission.
		//The onreadystatechange property/method is set to a function that is called on state change.
		//For any data request it is set to the generic serverResponse function, with a custom-defined property, requestType.
		xmlHTTPObject.onreadystatechange = serverResponse;
		if (exportOnly == true){
			xmlHTTPObject.requestType = 'export';
		}else{
			xmlHTTPObject.requestType = 'data'; //custom defined property specifying what request type has been sent
		}
		
		//Next line establishes a http connection with the php webpage on server.
		xmlHTTPObject.open("POST", "/php/getECHData.php", true);
		//specifies the protocol used. I don't exactly know what it means, but i copied it from a tutorial and it works for returning a string.
		xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
		//The string request is then sent to the php webpage.
		var sendStr = "request=" + requestType + "&session=" + sessionID + "&startTime=" + startTime + "&endTime=" + endTime + "&interval=" + interval + "&calibrations=" + calibrations + "&export=" + exportOnly + "&channels=" + channelString;
    xmlHTTPObject.timeout = 120000;
    xmlHTTPObject.ontimeout = requestTimeout;
    xmlHTTPObject.send(sendStr);
	}
  
  function requestTimeout(){
    hideLoader();
    alert("Request to server timed out.");
  }

	function requestWrapper(tab){
		showLoader();
		//gets information from the user input and puts it into the requried form for the above function
		var requestType = tab.requestType;
		var sessionID = tab.sessionID;
		var startTime = tab.startTime;
		var endTime = tab.endTime;
		var calibrations = tab.calibrations;
		var channelString = tab.channelString;
		
		var interval = tab.interval;
		if (interval == "ALL DATA"){
			interval = 0;
		}else if (interval == "" || interval == "default"){
			interval = "NULL";
		}
		
		if (tab.type == 'CSV'){
			var exportOnly = true;
		}else{
			var exportOnly = false;
		}
		//put all gathered data into a request to the sever by calling the above function.
		sendDataRequest(requestType, sessionID, startTime, endTime, interval, calibrations, exportOnly, channelString);
	}
	
	function sendUpdateRequest(tab){	
		var xmlHTTPObject = new XMLHttpRequest();
		xmlHTTPObject.onreadystatechange = serverResponse;
		xmlHTTPObject.requestType = 'update'; 
		var calibrations = tab.calibrations;
		var channelString = tab.channelString;
    var sessionID = tab.sessionID;

		xmlHTTPObject.open("POST", "/php/getECHData.php", true);
		xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
		var sendStr = "request=update&calibrations=" + calibrations + "&session=" + sessionID + "&channels=" + channelString;
    xmlHTTPObject.timeout = 5000;
		xmlHTTPObject.send(sendStr);
	}	
		
	//This is the generic function that is exectued whenever the server returns a response to a request.
	//Response is a string of text, (if transmission successful).
	//This function simply chooses what other function to call to handle the returned string.
	function serverResponse(){
		
			//a readyState of 4 signifies that the data was transmitted and now a response has been recieved.
			//status = 200 signifies that the data receieved is 'OK'.
			if  (this.readyState == 4 && this.status == 200){
				request = this.requestType;
				//the responseText property contains the returned string of data from the web server.
				var responseStr = this.responseText;	
        if (responseStr === "1"){
          alert("Server database access error. Please try again. If problem persists, visit Troubleshooting page.");
          return;
        }
        
				switch  (request){
					case 'data':
              alert(responseStr);
							dataResponse(responseStr);
					break;
					case 'export':
							exportResponse(responseStr);
					break;
					case 'sessions':
							sessionResponse(responseStr);
					break;
					case 'update':
							updateResponse(responseStr);
					break;
					case 'channels':
							channelResponse(responseStr);
					break;
					default:
				}
			}
	}
	
	function exportResponse(responseStr){
			if (createDataObject(responseStr, true) == true){
        exportDataObject(exportData, false);
      }
			hideLoader();
	}
	
	function dataResponse(responseStr){
			if (createDataObject(responseStr, false) == true){
        populateChart(activeTab.tabData);
        if (activeTab.liveUpdates == true){
          var interval = getDataInterval(activeTab);
          liveUpdatesIntervalID = setInterval(sendUpdateRequest, interval, activeTab);
        }
      }
			hideLoader();
	}
	
	function getDataInterval(tab){
		//1st try and read interval from tab.interval property - if not determinable from it go onto data point time spacing, if that's not possible use default value of 10s.
		if (tab.interval != 'default' && tab.interval != 'ALL DATA'){
			return tab.interval * 1000;
		}else{
			for (var i=0; i < tab.tabData.length; i++){
				if (tab.tabData[i].data.length >= 2){
					var latestPoint = tab.tabData[i].data.length -1;
					var interval = (tab.tabData[i].data[latestPoint].x - tab.tabData[i].data[0].x) / (tab.tabData[i].data.length -1);
					return interval;
				}
				if (i = tab.tabData.length - 1){
					//no interval able to be obtained as not enough data present. set to default 10s
					return 10000;
				}
			}
			//in case tab.tabData.length == 0, return default 10000.
			return 10000;
		}
	}
	
	function updateResponse(responseStr){
		chartData = activeTab.tabData;
		//get rid of the error message - it will already be displayed.
    try{
      if (responseStr == ""){
        return;
      }
      var splitResponse= responseStr.split("<P3>");
    
      //get channels
      var channelStrings = splitResponse[0].split("<P1>");
      //for each channel
      for (var channelNum = 0; channelNum < channelStrings.length; channelNum++){
        var tempSplit = channelStrings[channelNum].split("<P2>");
        var channelName = tempSplit[0];
        var channelData = tempSplit[1].split(",");
        var calibrationData = tempSplit[2];
        
        var datasetNum = -1;
        //need to find channel in tabData object, then append tabData and scatterChart
        for (var num = 0; num < chartData.length; num++){
          if (chartData[num].name == channelName){
            datasetNum = num;
            break;
          }
        }
        if (datasetNum < 0){
          //no dataset found for channel
          continue;
        }
        //if chanData does not have any data in it, do not want to add data to this dataset, doing so messes it up.
        if (tempSplit[1] == ""){
          continue;
        }
        //data is an array of point objects.
        //each point in data has 2 properties, x and y, and an optional 3rd, r. 
        //don't want to transfer erroneous readings that will mess up automatic scale of graph.
        maxPoint = chartData[datasetNum].data.length -1;			
        if ((!(channelData[1] > 1000000 || channelData[1] < -1000000)) && chartData[datasetNum].data[maxPoint].x != channelData[0]){
          //data not erroneous and is not same as current last data point i.e. its new data.
          var newData = {};
          newData.x = channelData[0];
          newData.y = channelData[1];
          chartData[datasetNum].data.push(newData);
          scatterChart.datasets[datasetNum].addPoint(newData.x, newData.y);
        }	
      }
      scatterChart.update();
    }catch(err){
      alert("Error in the transmission format from the server.");
    }
	}
	
	function createDataObject(responseStr, exportOnly){
		//attempt to free up webpage memory by deleting chart. - not much effect if any.
		scatterChart = {}; 
		//set up chartData array of dataset objects which will use later.
		var chartData = [];
		var numDatasets = 0;
		
		//setting up an array of colors, which is used to specify the color of channel data displayed on the graph.
		var myColor = ['Black', 'Brown', 'Red', 'Orange', 'Yellow', 'Green', 'Blue', 'Violet', 'Gray', 'Cyan',
					 'Gold', 'Silver', 'Aqua', 'Crimson', 'DarkBlue', 'DarkMagenta', 'DarkRed', 'DarkSalmon', 'HotPink', 'IndianRed',
					 'LawnGreen', 'LightSeaGreen', 'LightSteelBlue', 'Lime', 'Maroon', 'MidnightBlue', 'MediumSpringGreen', 'Olive', 'Peru', 'Purple',
					 'RoyalBlue', 'Teal', 'Tomato', 'YellowGreen', 'Thistle'];

		//parse off the potential calibration error message.
    try{
      if (responseStr == ""){
        throw "No data";
      }
      var p0split = responseStr.split("<P0>");
      
      var channelInfo = p0split[0];
      if (channelInfo == ""){
        throw "No data";
      }

      var channelStrings = channelInfo.split("<P1>");
      for (var channelNum = 0; channelNum < channelStrings.length; channelNum++){
        var tempSplit = channelStrings[channelNum].split("<P2>");
        var channelName = tempSplit[0];
        var slope = tempSplit[1];
        var offset = tempSplit[2];
        chartData[numDatasets] = new dataSet();
        chartData[numDatasets].name = channelName;
        chartData[numDatasets].label = channelName;
        //giving the datasets nice colors.
        //Sets 0-9 are colored according to the resistor color code. except 9-white.
        if (numDatasets <= 34){
          chartData[numDatasets].strokeColor = myColor[numDatasets];
          chartData[numDatasets].pointColor = myColor[numDatasets];
        } else{
          chartData[numDatasets].strokeColor = myColor[numDatasets % 35];
          chartData[numDatasets].pointColor = myColor[numDatasets % 35];
        }
        if ((slope == 'NULL') || (offset == 'NULL')){
          //setting whether calibrations are set or not.
          chartData[numDatasets].calibrations = false;						
        }else{
          chartData[numDatasets].calibrations = true;
          chartData[numDatasets].slope = slope;
          chartData[numDatasets].offset = offset;
        }
        numDatasets++;
      }
      
      var errMessage = p0split[1];
      var errLabel = document.getElementById('errMessage');
      errLabel.innerHTML = errMessage;
      chartData.errMessage = errMessage;
      
      var numColumns = numDatasets + 1;
      
      if (p0split[2] == ""){
        throw "No data";
      }
      var rows = p0split[2].split("<P1>");
      for (var rownum=0; rownum < rows.length; rownum++){
        var cols = rows[rownum].split(",");
        for (var colnum=1; colnum < numColumns; colnum++){
          //don't want to transfer erroneous readings that will mess up automatic scale of graph.
          //reject extreme readings, or any with time < 1000s i.e. at or around 0 which is clearly erroneous.
          if (!(cols[colnum] == "" || cols[colnum] > 1000000 || cols[colnum] < -1000000 || cols[0] < 1000000)){
            var dataPoint = {};
            dataPoint.x = cols[0];
            dataPoint.y = cols[colnum];
            //adding new point to dataset:
            chartData[colnum - 1].data.push(dataPoint);
          }	
        }
      }
    }catch(err){
      if (err == "No data"){
        alert("No data recieved from server for specified session.");
      }else{
        alert("Error in the transmission format from the server.");
      }
      return false;
    }
		if (exportOnly == true){
			exportData = chartData;
		}else{
			activeTab.tabData = chartData;
		}
    return true;
	}
	
	function populateChart(chartData){
		//this should put all the data into the chartData array of dataset objects.
		//now to generate the graph.
		//This call generates and displays the new chart with the data from the chartData dataset array.
		var options = {
			//these are the additional options that have been specified. There are more options you can specify
			//and these can be found in the Chart.js and chart.js.scatter documentations. 
			animation: false,
			scaleGridLineColor: "rgba(0,0,0,.3)",
			scaleLineColor: "rgba(0,0,0,.3)",
			scaleDateFormat: "dd/mm/yy",
			scaleTimeFormat: "HH:MM:ss",
			scaleDateTimeFormat: "HH:MM:ss dd/mm/yyyy",
			useUtc: true,
			bezierCurve: false,
			scaleType: 'date',
			datasetStroke: true,
			pointDotRadius: 0,
			scaleLabel: function (yNumber) {
				//puts all values on y scale to 3dp.
				return Number(yNumber.value).toFixed(3);
			},
			legendTemplate : function (){
			//this is the function that gets called when chart.generateLegend method is called.
				//first remove the existing legend.
				
				var legendContainer = document.getElementById("LegendList");
				while (legendContainer.firstChild){
					legendContainer.removeChild(legendContainer.firstChild);
				}
				//then create legend title.
				document.getElementById('legendDiv').style.visibility = 'visible';
				//then create color code for each channel's data.
				for (var dataSet = 0; dataSet < chartData.length; dataSet++){
						var tableRow = document.createElement('tr');
						var tableData = document.createElement('td');
						var spanTag = document.createElement('span');
						spanTag.style.background = chartData[dataSet].strokeColor;
						tableData.appendChild(spanTag);
						var listText = chartData[dataSet].label;
						var textNode = document.createTextNode(listText);
						tableData.appendChild(textNode);
						tableRow.appendChild(tableData);   
						var tableData = document.createElement('td');
							tableData.innerHTML = "Hide";
							tableData.style.cursor = 'pointer';
							tableData.style.color = 'red';	
							tableData.onmouseover = underline;
							tableData.onmouseout = ununderline;
							tableData.value = dataSet;
							tableData.onclick = hideChannel;
						tableRow.appendChild(tableData)
						legendContainer.appendChild(tableRow);
				}
			}
		};
		applyScale(chartData, activeTab.yMax, activeTab.yMin, options);
		scatterChart = new Chart(document.getElementById("chartCanvas").getContext("2d")).Scatter(chartData, options);
		//This method executes the code in the legendTemplate
		scatterChart.generateLegend();
		document.getElementById('chartCanvas').style.visibility = 'visible';
	}

	function channelResponse(responseStr){
		//first parse response into each logger response.
    try{
      if (responseStr == ""){
        alert("No channel information was received from server.");
        return;
      }
      var slaveStrings = responseStr.split("<P0>");
      var slaves = [];
      //for each slave:
      for (var i= 0; i < slaveStrings.length; i++){
        slaves[i] = {};
        slaves[i].channelNameArray = [];
        slaves[i].channelIDArray = [];
        var channelStrings = slaveStrings[i].split("<P1>");
        //allocatign slaveID and channel names.
        slaves[i].addr = channelStrings[0];
        for (var j = 1; j < channelStrings.length; j++){
          var tempArray = channelStrings[j].split("<P2>");
          slaves[i].channelIDArray[j-1] = tempArray[0];
          slaves[i].channelNameArray[j-1] = tempArray[1];
        }
      }
      //now each slave object contains channelName array, channelIDArray and Addr properties.

      //now to populate the html table.
      //first clear it.
      var channelTable = document.getElementById('channelTable');
      channelTable.innerHTML = "";
      
      //for each logger, populate column. if row doesn't exist, create it.
      var numRows = 0;
      for (var i= 0; i < slaves.length; i++){
        if (numRows == 0){
          var tr = document.createElement('tr');
          channelTable.appendChild(tr);
          numRows++;
        }
        var cell = document.createElement('td');
        var cellText = document.createTextNode(slaves[i].addr);
        cell.appendChild(cellText);
        cell.onclick = changeColumnColor;
        cell.style.cursor = 'pointer';
        channelTable.firstElementChild.appendChild(cell);
        
        //for each channel of slave:
        for (var j = 0; j < slaves[i].channelIDArray.length; j++){
          //if row doesnt exist, create it.
          if ((j+1)  > (numRows-1)){
            var tr = document.createElement('tr');
            channelTable.appendChild(tr);
            numRows++;
          }
          var cell = document.createElement('td');
          var cellText = document.createTextNode(slaves[i].channelNameArray[j]);
          cell.appendChild(cellText);
          cell.channelID = slaves[i].channelIDArray[j];
          cell.onclick = changeBackground;
          cell.style.cursor = 'pointer';
          cell.style.backgroundColor = 'lime';
          channelTable.children[j+1].appendChild(cell);
        }
      }
      //table populated, count channels.
      countChannels(channelTable.firstElementChild.firstElementChild);
    }catch(err){
      alert("Error in the transmission format from the server.");
    }
	}
	
	function sessionResponse(responseStr){

		//server returns response string consisting of comma delimited data in following form:
		//session1info<P0>session2info<P0>...sessionNinfo
		//each sessioninfo consists of: id<P1>name<P1>startTime
		try{
      if (responseStr == ""){
        alert("No session information was receieved from the server.");
        return;
      }
      var  sessionStr = responseStr.split("<P0>");
      //creating table rows and data cells and appending them to sessions table.
      var tableRow = {};
      var tableData = {};
      //for each session.
      for (var i=0; i < sessionStr.length; i++){
        var sessionData = sessionStr[i].split("<P1>");
        tableRow = document.createElement('tr');
        tableRow.onclick = function(){
          var nextRow = document.getElementById('sessionBody').firstElementChild;
          while (nextRow !== null){
            nextRow.style.backgroundColor = 'white';
            nextRow = nextRow.nextElementSibling;
          }
          this.style.backgroundColor = 'lime';
          document.getElementById('rangeText').innerHTML = this.children[1].innerHTML;
        };
        for (var j=0; j<sessionData.length; j++){				
          tableData = document.createElement('td');
          var tableText = document.createTextNode(sessionData[j]);
          tableData.appendChild(tableText);
          tableRow.appendChild(tableData);
        }
        document.getElementById('sessionBody').appendChild(tableRow);  
      }
    }catch(err){
      alert("Error in the transmission format from the server.");
    }
	}
	
	function underline(){
		this.style.textDecoration = 'underline';
	}
	function ununderline(){
		this.style.textDecoration = 'none';
	}
	
	function changeBackground(){
		if (this.style.backgroundColor == 'red'){
			this.style.backgroundColor = 'lime';
		}else{
			this.style.backgroundColor = 'red';
		}
		countChannels(this);
	}
	
	function changeColumnColor(){
		//if any element in column = red, change all to green, else all is green so change to red.
		//find elements node number:
		var nodeNum = Array.prototype.indexOf.call(this.parentNode.children, this);
		//got it.
		//Now loop through nodes to see if any red.
		var anyRed = false;
		var nextRow = this.parentNode.nextElementSibling;
		while (nextRow !== null){
			if (nextRow.children[nodeNum].style.backgroundColor == 'red'){
				anyRed = true;
				break;
			}
			nextRow = nextRow.nextElementSibling;
		}
		
		if (anyRed == true){
			//change all to green.
			var nextRow = this.parentNode.nextElementSibling;
			while (nextRow !== null){
				if (nextRow.children[nodeNum].style.backgroundColor == 'red'){
					nextRow.children[nodeNum].style.backgroundColor = 'lime';
				}
				nextRow = nextRow.nextElementSibling;
			}
		}else{
			//change all to red.
			var nextRow = this.parentNode.nextElementSibling;
			while (nextRow !== null){
				if (nextRow.children[nodeNum].style.backgroundColor == 'lime'){
					nextRow.children[nodeNum].style.backgroundColor = 'red';
				}
				nextRow = nextRow.nextElementSibling;
			}
		}	
		
		countChannels(this);
	}
	
	function countChannels(datacell){
		//go through each row and add up number that have green background i.e. number selected.
		var numcols = datacell.parentNode.children.length;
		var numchannels = 0;
		var nextRow = datacell.parentNode.parentNode.firstElementChild;
		while (nextRow !== null){
			for (var i=0; i<numcols; i++){
				if (nextRow.children[i].style.backgroundColor == 'lime'){
					numchannels++;
				}
			}
			nextRow = nextRow.nextElementSibling;
		}
		document.getElementById('channelLabel').innerHTML = "Number of channels: " + numchannels;
		document.getElementById('channelsText').innerHTML = numchannels;
	}

	function getChannelString(){
	var channelString = "";
		var table = document.getElementById('channelTable');
		var nextRow = table.firstElementChild;
		if (nextRow == null){
			return;
		}
		var colNums = nextRow.childNodes.length;
		var first = true;
		for (var col = 0; col < colNums; col++){	
			var colString = "";
			nextRow = table.firstElementChild;
			//looping down each column
			while (nextRow !== null){
				if (nextRow.children[col].style.backgroundColor == 'lime'){
					if (first == false){
						colString += "<P1>";
					}else{
						first = false;
					}
					colString += nextRow.children[col].channelID;
				}
				nextRow = nextRow.nextElementSibling;
			}
			//end of column, put colString onto channelString.
			channelString += colString;
		}
		//should now have returned the channelString which will be sent with requests to the php file on server.
		return channelString;
	}
	
	//This function populates the list of sessions displayed when the session checkbox is checked.
	function loadSessions(){
		//first delete sessions displayed
		var sTable = document.getElementById("sessionBody");
		while (sTable.firstChild) {
			sTable.removeChild(sTable.firstChild);
		}
		
		//Next request data from the server regarding data from the database table that stores information about all the sessions.
		var xmlHTTPObject = new XMLHttpRequest();
		xmlHTTPObject.requestType = 'sessions';
		xmlHTTPObject.onreadystatechange = serverResponse;
		
		//Opening server connection and sending data:
		xmlHTTPObject.open("POST", "/php/getECHData.php", true);
		xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xmlHTTPObject.timeout = 30000;
    xmlHTTPObject.ontimeout = requestTimeout;
		xmlHTTPObject.send("request=sessions");
	}

	//This function executes when the live checkbox is clicked.
	function liveChange(){
		if (document.getElementById('liveCheck').checked == true){
			//setinterval function makes updateData function execute every 1000ms
			//live = setInterval("updateData()", 1000);
		}else{
			//if the checkbox gets unchecked, clearinterval function stops updateDate function from executing every 1000ms.
			//clearInterval(live);
		}
	}
	
	//This function is called when a chart is already loaded, and you want to add on data points to the end of the graph,
	//without reloading the whole thing.
	function updateData(chartData){
	
		//First a request needs to made to the server. This consists of comma delimited data in the form of:				
		//logger1ID,logger1latestDatatime,logger2id,logger2latestDatatime.....loggerNID, loggerNlatestdataTime.
		//define output string
		var outString = "";
		
		//for each loggerData object, output the loggerID and the latest measurement time for that logger in comma delimited format.
		var lastLoggerID = '';
		var lastLoggerMaxTime = 0;
		for (var dataSet=0; dataSet < scatterChart.datasets.length; dataSet++ ){
			//if new logger in session, reset loggername in storage and its associated latest time
			//LoggerID and its associated latest time are then outputted when the end of the logger's datasets reached
			if (chartData[dataSet].logger != lastLoggerID){
				
				//if not first loop produce output.
				if (dataSet > 0){
				
					//new loggerID, therefore have correct latest data time for last logger, therefore add the last logger stats to output.
					if (outString == ""){
						outString += lastLoggerID + "," + (lastLoggerMaxTime/1000);
					}else{
						outString += "," + lastLoggerID + "," + (lastLoggerMaxTime/1000);
					}
				}
			
				//Refresh the statistics so analysis can be repeated for next logger in session.
				lastLoggerID = chartData[dataSet].logger;
				//if dataset does not have points, latesttime = 0
				if (scatterChart.datasets[dataSet].points.length == 0){
					lastLoggerMaxTime = 0;
				}else{
					lastLoggerMaxTime = scatterChart.datasets[dataSet].points[scatterChart.datasets[dataSet].points.length - 1].arg;
				}
			}else{
			//must be same logger, check for newmaxtime.
				//if dataset contains no points, do nothing
				if (scatterChart.datasets[dataSet].points.length > 0){
					if (scatterChart.datasets[dataSet].points[scatterChart.datasets[dataSet].points.length - 1].arg > lastLoggerMaxTime){
						lastLoggerMaxTime = scatterChart.datasets[dataSet].points[scatterChart.datasets[dataSet].points.length - 1].arg;
					}
				}
			}
		}
		//the above loop produces required ouput for all loggers in session apart from the last one.
		//Therefore we need to add it on.
		if (outString == ""){
			outString += lastLoggerID + "," + (lastLoggerMaxTime/1000);
		}else{
			outString += "," + lastLoggerID + "," + (lastLoggerMaxTime/1000);
		}
		//should now have correct output		
		
		//got the data to send, now need to send it.
		var xmlHTTPObject = new XMLHttpRequest();
		xmlHTTPObject.requestType = 'update';
		xmlHTTPObject.onreadystatechange = serverResponse; //generic server response function.
		xmlHTTPObject.open("POST", "/php/getECHData.php", true);
		xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
		var sendStr = "request=update&session=" + globSessionID + "&info=" +outString;
    xmlHTTPObject.timeout = 5000;
		xmlHTTPObject.send(sendStr);
	}
	
	function channelRequest(type, startTime, endTime, sessionID){
		//first get startTime, endtime.
		if (startTime == ""){
			startTime = "NULL";
		}else{
			var sDate = new Date(startTime);
			startTime = (sDate.getTime())/1000;
		}
		if (endTime == ""){
			endTime = "NULL";
		}else{
			var eDate = new Date(endTime);
			endTime = (eDate.getTime())/1000;
		}
		
		if (type == "session"){
			//a session channel request.
			var sendStr = "request=channels&startTime=" + startTime + "&endTime=" + endTime + "&input=session&session=" + sessionID;
		}else{
			//a timescale channel request
			var sendStr = "request=channels&startTime=" + startTime + "&endTime=" + endTime + "&input=timescale";
		}

		var xmlHTTPObject = new XMLHttpRequest();
		xmlHTTPObject.requestType = 'channels';
		xmlHTTPObject.onreadystatechange = serverResponse; //generic server response function.
		xmlHTTPObject.open("POST", "/php/getECHData.php", true);
		xmlHTTPObject.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xmlHTTPObject.timeout = 20000;
    xmlHTTPObject.ontimeout = requestTimeout;
		xmlHTTPObject.send(sendStr);
	}
	
	function channelRequestWrapper(){
    var requestType = 'session';
    var startTime = "";
    var endTime = "";
    var nextRow = document.getElementById('sessionBody').firstElementChild;
    while (nextRow !== null){
      if (nextRow.style.backgroundColor == 'lime'){
        var sessionID = nextRow.firstElementChild.innerHTML;
        break;
      }
      nextRow = nextRow.nextElementSibling;
    }
		channelRequest(requestType, startTime, endTime, sessionID);
	}
	
	function exportDataObject(dataObject, fromGraph){
		var loggersArray = getLoggers(dataObject);
		//for each logger in loggersArray, populate it with data.
		for (var num = 0; num < loggersArray.length; num++){
			produceLoggerArray(loggersArray[num], dataObject);
		}
		//then create output string:
		var outputString = outputToString(loggersArray);
		//works up til here.

		//now need to save the outputString to a .csv file.
		//this instantiates a blob object which is required for saving a file (easily).
		//blob.js is supposed to be multi-platform
		var myBlob = new Blob([outputString]);
		//next save the blob as the specified file - uses the saveAs method from the filesaver library/
		if (fromGraph == true){
			var saveString = activeTab.children[0].innerHTML;
			resetForm();		
		}else{
			var saveString = document.getElementById('rangeText').innerHTML;
			resetForm();		
			resetMenu();
		}
		saveString = saveString + ".csv";
		saveAs(myBlob, saveString);
	}

	//This function returns an associative array of the loggers, (with loggerIDs as keys), each element being an object, with a ChannelNums property,
	//which contains an indexed array of channels containing the dataset numbers of each channel.
	function getLoggers(chartData){
		var Loggers = [];
		//loop through datasets, (channels), assigning each one to their respective logger.
		//datasets contained as elementes of chartData array
		for (var dataset = 0; dataset < chartData.length; dataset++){
			var loggerID = chartData[dataset].logger;
			loggerNum = findLogger(Loggers, loggerID);
			//create ChannelNums array element corresponding to the channel. This will be used to reference the dataset when data being
			//extracted for each logger.
			Loggers[loggerNum].ChannelNums.push(dataset);
			Loggers[loggerNum].ChannelNames.push(chartData[dataset].name);
		}
		return Loggers;
	}


	function findLogger(loggerArray, loggerID){
		//returns logger array index if exists, else returns value to insert at.
		//and creates the object at that point.
		for (var num = 0; num < loggerArray.length; num++){
			if (loggerArray[num].loggerID == loggerID){
				return num;
			}
		}
		//if reaches here, element in loggers array with loggerID does not exist.
		//therefore create one, and return index number.
		var newIndex = loggerArray.length;
		loggerArray[newIndex] = {};
		loggerArray[newIndex].loggerID = loggerID;
		loggerArray[newIndex].ChannelNums = [];
		loggerArray[newIndex].ChannelNames = [];
		return newIndex;
	}

	function produceLoggerArray(loggerObject, chartData){
		//first instantiate logger output array
		loggerObject.Output = [];
		
		//create property to hold indexes of each channel dataset that we are looping through.
		//also set the Output array 0th row to hold the headers.
		loggerObject.Output[0] = [];
		loggerObject.ChannelIndexes = [];
		loggerObject.Output[0].push('Time'); //0th column header.
		for (var chan = 0; chan < loggerObject.ChannelNums.length; chan++){
			//setting initial index of each channel to 0.
			loggerObject.ChannelIndexes[chan] = 0;
			loggerObject.Output[0].push(loggerObject.ChannelNames[chan]);
		}
		
		//now need to find the channel(s) with the minimum time at their array indexes, and then add this to logger output
		
		//output will be pushed with a temporary array which will contain channel data points with the minimum time.
		
		//loop through all datapoints in datasets (channels) - the while loop will exit once all of the channels have been scanned and uploaded to object output array.
		while(true){
			//first find minimum time.
			var minTime = 0;
			//go through each channel, store data in tempArray until find a lesser time, in which case replace data array.
			for (var chan = 0; chan < loggerObject.ChannelNums.length; chan++){
					//get data from graph
					if (!(typeof chartData[loggerObject.ChannelNums[chan]].data[loggerObject.ChannelIndexes[chan]] === 'undefined')){
						if (minTime == 0){
							//i.e. if not set yet.
							minTime = chartData[loggerObject.ChannelNums[chan]].data[loggerObject.ChannelIndexes[chan]].x;
						}else{
							if (chartData[loggerObject.ChannelNums[chan]].data[loggerObject.ChannelIndexes[chan]].x < minTime){
								minTime = chartData[loggerObject.ChannelNums[chan]].data[loggerObject.ChannelIndexes[chan]].x;
							}
						}
					}
				
			}

			//if minTime = 0, all channels undefined, exit loggerLoop.
			if (minTime == 0){
				return;
				//function has executed and logger object has been returned with Output array containing logger data to export
				//error values are exported as blank fields in array "".
				//could additionally add a property specifying the channelHeaders/names.
			}
			//else is content
			//put all datasets with value for mintime into a temporary array
			var tempArray = [];
			//put minTime into tempArray
			tempArray.push(minTime);
			
			for (var chan = 0; chan < loggerObject.ChannelNums.length; chan++){
				//first need to test if point defined, if not output "".
				
					//not export only. Getting data as is displayed on chart.
					if (!(typeof chartData[loggerObject.ChannelNums[chan]].data[loggerObject.ChannelIndexes[chan]] === 'undefined')){
						if (chartData[loggerObject.ChannelNums[chan]].data[loggerObject.ChannelIndexes[chan]].x == minTime){
							//add to array
							tempArray.push(chartData[loggerObject.ChannelNums[chan]].data[loggerObject.ChannelIndexes[chan]].y);
							//increment index number
							loggerObject.ChannelIndexes[chan]++;
						}else{
						tempArray.push("");
						}
					}else{
						//point undefined - i.e. does not exist - output "".
						tempArray.push("");
					}
				
			}
			//add tempArray to logger output array
			loggerObject.Output.push(tempArray);
		}	
	}
	
	function outputToString(loggersArray){
		//go through each row for each loggers output
		//export each loggeroutput row with tab in between
		
		//the output string:
		var outputString = "";
		var loggerOutput = true; //boolean representing if any logger outputted data. if == false then loop ends.
		
		//for each row:
		var row = 0;
		while (loggerOutput == true){
			loggerOutput = false;
			
			//for each logger.
			for (var num = 0; num < loggersArray.length; num++){
				//if data row exists:
				if (!( typeof loggersArray[num].Output[row] === 'undefined')){
					//output tab delimited output data row
					//for each data row array:
					for (var col = 0; col < loggersArray[num].Output[row].length; col++){
						if (col == 0 && row > 0){
							//is time array - at the moment is UTC in ms, need to make into date.
							outputString += ((((loggersArray[num].Output[row][col] / 1000) + 2208988800) / (3600 * 24))+2) + ',';
							//var d = new Date(loggersArray[num].Output[row][col]);
							//outputString += d.toLocaleDateString() + " " + d.toLocaleTimeString() + ',';
						}else{
							outputString += loggersArray[num].Output[row][col] + ',';
						}
					}
					loggerOutput = true;
				}else{
					//row doesn't exist - output n tabs where n = numchannels.
					//row 0 should always exist if this function is being called.
					for (var col = 0; col < loggersArray[num].Output[0].length; col++){
						outputString += ',';
					}
				}
				//at end output blank column
				outputString += ',';
			}
			//at end output carriage return.
			outputString += '\r\n';
			//increment row
			row++;
		}
		return outputString;
	}
	
	function hideChannel(){
		//gets dataset from this object
		dataset = this.value;
		//if hiddenchannels array not defined, define it.
		if (typeof hiddenChannels === 'undefined'){
			hiddenChannels = [];
		}
		
		//initialise hiddenChannels array for dataset
		hiddenChannels[dataset] = [];
		//fill it with data
		var numPoints = scatterChart.datasets[dataset].points.length;
		for (var num = 0; num < numPoints; num++){
			//copy to hiddenChannels array, then remove point
			hiddenChannels[dataset][num] = {};
			hiddenChannels[dataset][num].x = scatterChart.datasets[dataset].points[0].arg;
			hiddenChannels[dataset][num].y = scatterChart.datasets[dataset].points[0].value;
			scatterChart.datasets[dataset].removePoint(0);
		}	
		scatterChart.update();
		this.innerHTML = "Show";
		this.style.color = 'lime';
		this.onclick = showChannel;
	}

	function showChannel(){
		//gets dataset from this object
		dataset = this.value;
		for (var num = 0; num < hiddenChannels[dataset].length; num++){
			//copy from hiddenChannels array, then free hiddenChannels array.
			scatterChart.datasets[dataset].addPoint(hiddenChannels[dataset][num].x, hiddenChannels[dataset][num].y);
		}	
		hiddenChannels[dataset] = [];
		scatterChart.update();
		this.innerHTML = "Hide";
		this.style.color = 'red';
		this.onclick = hideChannel;
	}
	
	function applyCalibrations(chartData){
	
		//go through each channel/dataset.
		var errMessage = "";
		for (var dataset = 0; dataset < chartData.length; dataset++){
			if (chartData[dataset].calibrations == true){
				//calibrations enabled.
				//go through scatterchart dataset and edit the point values.
				//for each point 
				for (var pointnum = 0; pointnum < scatterChart.datasets[dataset].points.length; pointnum++){
					//parsefloat necessary since otherwise javascript thinks we're attempting concatenation.
					scatterChart.datasets[dataset].points[pointnum].value = (scatterChart.datasets[dataset].points[pointnum].value * chartData[dataset].slope) + parseFloat(chartData[dataset].offset);
				}
				//do for chartData object as well
				for (var pointnum = 0; pointnum < chartData[dataset].data.length; pointnum++){
					//parsefloat necessary since otherwise javascript thinks we're attempting concatenation.
					chartData[dataset].data[pointnum].y = (chartData[dataset].data[pointnum].y * chartData[dataset].slope) + parseFloat(chartData[dataset].offset);
				}
			}else{
				//no calibration data exists for this. 
				if (errMessage == ""){
					errMessage = "No calibration data exists for: " + chartData[dataset].label;
				}else{
					errMessage += ", " + chartData[dataset].label;
				}
			}
		}
		//update chart.
		var errLabel = document.getElementById('errMessage');
		errLabel.innerHTML = errMessage;
		errLabel.style.visibility = 'visible';
		scatterChart.update();
	}
	
	function removeCalibrations(chartData){
		//go through each channel/dataset.
		for (var dataset = 0; dataset < chartData.length; dataset++){
			if (chartData[dataset].calibrations == true){
				//if calibrations were enabled.
				//go through scatterchart dataset and edit the point values.
				//for each point 
				for (var pointnum = 0; pointnum < scatterChart.datasets[dataset].points.length; pointnum++){
					scatterChart.datasets[dataset].points[pointnum].value = (scatterChart.datasets[dataset].points[pointnum].value - chartData[dataset].offset) / chartData[dataset].slope;
				}
				//update chartData object as well
				for (var pointnum = 0; pointnum < chartData[dataset].data.length; pointnum++){
					chartData[dataset].data[pointnum].y = (chartData[dataset].data[pointnum].y - chartData[dataset].offset) / chartData[dataset].slope;
				}
			}
		}
		//update chart.
		scatterChart.update();
	}	
	
	function updateSettingString(){
		settingstring = "";
		if (document.getElementById('liveCheck').checked == false){
			settingstring += "No live updates";
		}else{
			settingstring += "Live updates enabled";
		}
		if (document.getElementById('calibrationCheckbox').checked == false){
			settingstring += ", no calibrations";
		}else{
			settingstring += ", calibrations enabled";
		}
		if (document.getElementById('intervalList').value == ""){
			settingstring += ", interval: default";
		}else{
			settingstring+= ", interval: " + document.getElementById('intervalList').value;
		}
		document.getElementById('settingsLabel').innerHTML = settingstring;
	}
	
	function adjustScale(ymin, ymax){
		var numSteps = 10;
		var stepWidth = (ymax - ymin) / numSteps;
		Chart.defaults.global.scaleSteps = numSteps;
		Chart.defaults.global.scaleStartValue = ymin;
		Chart.defaults.global.scaleStepWidth = stepWidth;
		Chart.defaults.global.scaleOverride = true;
		scatterChart.update;
	}
	
	/* Deprecated. function putDefaults(){
		var newDate = new Date(); 
		var timezoneOffset = newDate.getTimezoneOffset() * 60000; 
		var oneHrDate = new Date(newDate - timezoneOffset - 3600000); 
		//document.getElementById('timeScaleCheck').checked = true;
		//document.getElementById('startTime').value = oneHrDate.toISOString().substring(0,19);
		//timescaleChange();
		document.getElementById('sessionInput').style.visibility = 'hidden';
		document.getElementById('sessionInput').style.display = 'table-cell';
		//document.getElementById('timeScaleInput').style.display = 'table-cell';
	}*/

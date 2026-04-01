<?php
//$time_pre = microtime(true);
//echo print_r($_POST);
//die();
$db = new SQLite3('../Logging database.db');
$db->busyTimeout(100);

$postString = $_POST['request'];
//$postString = "session";
switch ($postString) {
	case "session":

		$startTime = $_POST['startTime'];
		$endTime = $_POST['endTime'];
		$sessionID = $_POST['session'];
		if ($_POST['calibrations'] == "true") {
			$calibs = true;
		} else {
			$calibs = false;
		}
		$chanArray = setUpChannelArray();
		$sqlStr = "SELECT * FROM SessionTable WHERE SessionID = " . $sessionID . ";";
		$row = @queryRowSQL($sqlStr, 5000, $db);
		if ($row == false) {
			//couldn't find session.
			echo "1";
			writeToErrorLog("Server database access error", 5);
			$db->close();
			die();
		}
		$sessionID = $row['SessionID'];
		getAndExportTableData($db, $sessionID, $startTime, $endTime, $chanArray, $calibs);

		break;

	case "update":

		$sessionID = $_POST['session'];
		if ($_POST['calibrations'] == "true") {
			$calibs = true;
		} else {
			$calibs = false;
		}
		$chanArray = setUpChannelArray();
		$dataArray = array();
		$sqlStr = "SELECT * FROM SessionTable WHERE SessionID = " . $sessionID . ";";
		$row = @queryRowSQL($sqlStr, 5000, $db);
		if ($row == false) {
			//couldn't find session.
			echo "1";
			writeToErrorLog("Server database access error", 5);
			$db->close();
			die();
		}
		$sessionID = $row['SessionID'];
		getIncrementalUpdate($dataArray, $db, $sessionID, $chanArray);
		if ($calibs == true) {
			$errString = applyCalibrations($dataArray, $db, $sessionID);
		}
		exportData($dataArray, $db, $sessionID);
		if ($calibs == true) {
			echo "<P3>" . $errString;
		}

		break;

	case "sessions":
		//echo sessions delimited by <P0>, sessionInfo delimited by <P1>
		$sqlStr = 'SELECT * FROM SessionTable;';
		$sessions = @queryResultSQL($sqlStr, 10000, $db);
		if ($sessions == false) {
			//couldn't find sessions.
			echo "1";
			writeToErrorLog("Server database access error", 7);
			$db->close();
			die();
		}
		$tempArray = $sessions->fetchArray(SQLITE3_NUM);
		$first = true;
		while ($tempArray != false) {
			if ($first == true) {
				$first = false;
			} else {
				echo "<P0>";
			}
			echo $tempArray[0] . "<P1>" . $tempArray[1] . "<P1>" . $tempArray[2];
			$tempArray = $sessions->fetchArray(SQLITE3_NUM);
		}
		//has echoed back csv data about sessionID,sessionName,StartTime

		break;

	case "channels":

		$startTime = $_POST['startTime'];
		$endTime = $_POST['endTime'];

		$dataArray = array();
		$sessionID = $_POST['session'];
		getTableChannels($dataArray, $db, $sessionID);
		exportChannels($dataArray);
		$db->close();

		break;
	default:
}
//$time_post = microtime(true);
//$time_elapsed = $time_post - $time_pre;
//echo ("Time elapsed generating page = " . $time_elapsed . " microseconds.<br>");
$db->close();
return;

function getAndExportTableData(&$db, $sessionID, $startTime, $endTime, $chanArray, $calibs)
{
	//if startTime/endTime = null, means no start or end time.
	//determining database query for table.
	$tableName = "Data_" . $sessionID;

	if ($_POST['channels'] == "ALL") {
		$sqlStr = "SELECT * FROM " . $tableName;
	} else {
		$colsToSelect = findColsToSelect($tableName, $db, $chanArray);
		if ($colsToSelect == "") {
			//no columns and therefore no data to retrieve from this table. return.
			return;
		}
		//so the SQL string is:
		$sqlStr = "SELECT Time, " . $colsToSelect . " FROM " . $tableName;
	}
	//so know what columns to select from table, now need to know what to have as the WHERE condition.
	//this will be affected solely by the interval.
	//best to do in sql since saves memory and performance.
	$condition = applyInterval($tableName, $db, $startTime, $endTime);

	//and add the conditions.
	$prevConditions = false;
	if ($condition != "") {
		$sqlStr .= " WHERE " . $condition;
		$prevConditions = true;
	}
	if ($startTime != 'NULL') {
		if ($prevConditions == false) {
			$sqlStr .= " WHERE Time >= " . $startTime;
			$prevConditions = true;
		} else {
			$sqlStr .= " AND Time >= " . $startTime;
		}
	}
	if ($endTime != 'NULL') {
		if ($prevConditions == false) {
			$sqlStr .= " WHERE Time <= " . $endTime;
			$prevConditions = true;
		} else {
			$sqlStr .= " AND Time <= " . $endTime;
		}
	}
	//conditions have been added.
	$sqlStr .= ";";
	$results = @queryResultSQL($sqlStr, 300000, $db);	//5 minute timeout.
	if ($results == false) {
		//statement didnt execute properly.
		echo "1";
		writeToErrorLog("Server database access error", 8);
		$db->close();
		die();
	}
	//have results, now need to echo them 1 row at a time. 
	//output format as follows:
	//Channelsinfo<P0>errorMessage<P0>Rows
	///Channels//info: channelInfo<P1>//channelInfo<P1>...
	//channelInfo: name<P2>slope<P2>offset
	//Rows: Row<P1>Row<P1>...
	//Row: value,value,value,...
	//Note: if calibrations enabled and no calibrations exist for a channel, channel data is not sent out.

	$colNum = $results->numColumns();
	$slopes = array();
	$offsets = array();
	$enabled = array();
	$enabled[0] = 0; //time value should always be reported.
	$errMessage = "";
	for ($i = 1; $i < $colNum; $i++) {
		if ($i != 1) {
			echo "<P1>";
		}
		$colName = $results->columnName($i);
		$calibString = retrieveCalibrations($colName, $db, $sessionID);
		$tempArray = explode(",", $calibString);
		if ($tempArray[0] == "NULL" or $tempArray[1] == "NULL") {
			//error retrieving calibrations - may not exist.
			if ($errMessage == "") {
				$errMessage .= $colName;
			} else {
				$errMessage .= "," . $colName;
			}
			//set enabled index to false. i.e. dont gather data for channel if calibs are enabled.
			$enabled[$i] = 1;
		} else {
			//calibs fine - set enabled index to true
			$enabled[$i] = 0;
		}
		echo $colName . "<P2>" . $tempArray[0] . "<P2>" . $tempArray[1];
	}
	echo "<P0>";
	if ($errMessage != "") {
		echo "No calibration data exists for channels: " . $errMessage;
	}
	echo "<P0>";

	if ($calibs == false) {
		//echo every channels data
		$resultRow = $results->fetchArray(SQLITE3_NUM);
		$first = true;
		while ($resultRow != false) {
			if ($first == false) {
				echo "<P1>";
			} else {
				$first = false;
			}
			for ($i = 0; $i < $colNum; $i++) {
				if ($i != 0) {
					echo ",";
				}
				echo $resultRow[$i];
			}
			$resultRow = $results->fetchArray(SQLITE3_NUM);
		}
	} else {
		//echo blank data values for channels without calibrations.
		$resultRow = $results->fetchArray(SQLITE3_NUM);
		$first = true;
		while ($resultRow != false) {
			if ($first == false) {
				echo "<P1>";
			} else {
				$first = false;
			}
			for ($i = 0; $i < $colNum; $i++) {
				if ($i != 0) {
					echo ",";
				}
				if ($enabled[$i] == 0) {
					echo $resultRow[$i];
				}
			}
			$resultRow = $results->fetchArray(SQLITE3_NUM);
		}
	}
	return;
	//works.
}

function getTableChannels(&$dataArray, &$db, $sessionID)
{
	//need to get a slaveID, ID and name for each channel to be output.
	$tableName = "ChannelInfo_" . $sessionID;
	//want to get channel headers
	$sqlString = "SELECT * FROM " . $tableName;
	$results = @queryResultSQL($sqlString, 10000, $db);
	if ($results == false) {
		//statement didnt execute properly.
		echo "1";
		writeToErrorLog("Server database access error", 9);
		$db->close();
		die();
	}

	$num = 0;
	$row = $results->fetchArray(SQLITE3_ASSOC);
	while ($row != false) {
		//going to put it into dataArray with a value of channelName to utilise existing dataArray code.
		$dataArray[$num] = array();
		$dataArray[$num]['SlaveAddr'] = $row['SlaveAddr'];
		$dataArray[$num]['ID'] = $row['ID'];
		$dataArray[$num]['Name'] = $row['Name'];
		$num++;

		$row = $results->fetchArray(SQLITE3_ASSOC);
	}
	//now have an array of channels assoc arrays containing ID, SlaveAddr, Name
}

function getIncrementalUpdate(&$dataArray, &$db, $sessionID, $chanArray)
{
	//if startTime/endTime = null, means no start or end time.
	//determining database query for table.
	$tableName = "Data_" . $sessionID;

	if ($_POST['channels'] == "ALL") {
		$sqlStr = "SELECT * FROM " . $tableName;
	} else {
		$colsToSelect = findColsToSelect($tableName, $db, $chanArray);
		if ($colsToSelect == "") {
			//no columns and therefore no data to retrieve from this table. return.
			return;
		}
		//so the SQL string is:
		$sqlStr = "SELECT Time, " . $colsToSelect . " FROM " . $tableName . "  WHERE ROWID = (SELECT MAX(ROWID) FROM " . $tableName . ");";
	}

	$results = @queryResultSQL($sqlStr, 10000, $db);
	if ($results == false) {
		//statement didnt execute properly.
		echo "1";
		writeToErrorLog("Server database access error", 10);
		$db->close();
		die();
	}
	//now to put data from each channel into the associative array.
	//to do this will loop through results
	//when storing data into array, if the field doesn't already exist, php will create it, so no need to worry about index not existing.

	$rowArray = $results->fetchArray(SQLITE3_NUM);
	while ($rowArray != false) {
		//for each row - loop through it and store values into associative array
		for ($col = 0; $col < count($rowArray); $col++) {
			//if associative array index for channel not set, have to create it.
			if (!isset($dataArray[$results->columnName($col)])) {
				$dataArray[$results->columnName($col)] = array();
			}
			array_push($dataArray[$results->columnName($col)], $rowArray[$col]);
		}
		$rowArray = $results->fetchArray(SQLITE3_NUM);
	}
	//done. This should store all data from tables into the loggerArray
}

function applyCalibrations(&$dataArray, &$db, $sessionID)
{
	//applies calibrations each channel, returns error message on ones that couldn't be calibrated. also, removes the channel from the array.
	$errMessage = "";

	foreach ($dataArray as $key2 => $value2) {
		if ($key2 === 'Time') {
			continue;
		}
		$calibString = retrieveCalibrations($key2, $db, $sessionID);
		$tempArray = explode(",", $calibString);
		if ($tempArray[0] == "NULL" or $tempArray[1] == "NULL") {
			//error retrieving calibrations - may not exist.
			if ($errMessage == "") {
				$errMessage .= $key2;
			} else {
				$errMessage .= "," . $key2;
			}
			//remove array key.
			unset($dataArray[$key2]);
			continue;
		}
		//if here, calibrations exist and values can be altered.
		$chanArrayLength = count($dataArray[$key2]);
		for ($num = 0; $num < $chanArrayLength; $num++) {
			$dataArray[$key2][$num] = ((float) $dataArray[$key2][$num] * (float) $tempArray[0]) + (float) $tempArray[1];
		}
	}
	return $errMessage;
}

function exportData(&$dataArray, &$db, $sessionID)
{
	//echo channel details separated by a parse1
	$first = true;
	//for each channel
	foreach ($dataArray as $key2 => $value2) {
		if ($key2 === 'Time') {
			continue;
		}
		if ($first == false) {
			echo "<P1>";
		} else {
			$first = false;
		}
		//echo channel name	
		echo $key2 . "<P2>";
		//for each channel data point: output time then value.
		$chanArrayLength = count($dataArray[$key2]);
		for ($num = 0; $num < $chanArrayLength; $num++) {
			if ($num != 0) {
				echo ',';
			}
			echo $dataArray['Time'][$num] . ',';
			echo $dataArray[$key2][$num];
		}
		//should have outputted all channel data points.
		//now echo a parse2 then output channel calibrations in form "<P2>slope,offset"
		echo "<P2>" . retrieveCalibrations($key2, $db, $sessionID);
	}
	//should have outputted data for all channels.
}

function exportChannels(&$dataArray)
{
	$first = true;
	//output format: slaveAdd<p1>chan1id<p2>chan1name<p1>chan2id<p2>chan2id<p1>...<p0>slaveadd2<P1>...
	$currentSlaveAddr = -1;
	//for each channel
	for ($i = 0; $i < count($dataArray); $i++) {
		if ($currentSlaveAddr != $dataArray[$i]['SlaveAddr']) {
			if ($i != 0) {
				echo "<P0>";
			}
			echo $dataArray[$i]['SlaveAddr'];
			$currentSlaveAddr = $dataArray[$i]['SlaveAddr'];
		}
		echo "<P1>" . $dataArray[$i]['ID'] . "<P2>" . $dataArray[$i]['Name'];
	}
}

function retrieveCalibrations($channelID, &$db, $sessionID)
{
	//returns string containing 'slope,offset'
	// 	$sqlString = "SELECT Slope, Offset FROM //ChannelInfo_" . $sessionID . " WHERE ID = " . $channelID . ";";
	//   $row = @queryRowSQL($sqlString, 5000, $db);	
	// 	if ($row == false or is_null($row['Slope']) or is_null($row['Offset'])){
	// 		//channel doesn't exist or slope or offset is null i.e. has no value.
	//     writeToErrorLog("Server database access error", 11);
	// 		return "NULL,NULL";
	// 	}
	// 	//else no error.
	// 	$slope = $row['Slope'];
	// 	$offset = $row['Offset'];
	return "1.0,1.0";
}

function applyInterval($tableName, &$db, $startTime, $endTime)
{
	//uses post interval variable.
	//if == 0, no interval specified, return all
	$interval = $_POST['interval'];

	//getting endTime.
	$sqlStr = "SELECT ROWID, Time FROM " . $tableName . " WHERE ROWID = 1;";
	$minRow = @queryRowSQL($sqlStr, 5000, $db);
	if ($minRow == false) {
		//no records exist in table, program will crash if tries to apply interval.
		return "";
	}
	$tableStartTime = $minRow['Time'];
	$sqlStr = "SELECT ROWID, Time FROM " . $tableName . " WHERE ROWID = (SELECT MAX(ID) FROM " . $tableName . ");";
	$maxRow = @queryRowSQL($sqlStr, 5000, $db);
	$tableEndTime = $maxRow['Time'];
	$numRows = $maxRow['ID'];
	if ($numRows == 0) {
		return "";
	}

	//extractEvery determines how frequently a row should be extracted from the DB
	//if no interval defined, define one that gives 500 points per dataset.
	if ($interval == "NULL") {
		if ($startTime == "NULL" and $endTime == "NULL") {
			$interval = ($tableEndTime - $tableStartTime) / 500;
		} elseif ($startTime == "NULL") {
			//endtime defined, no start time.
			$interval = ($endTime - $tableStartTime) / 500;
		} elseif ($endTime == "NULL") {
			//starttime defined, no end time.
			$interval = ($tableEndTime - $startTime) / 500;
		} else {
			//starttime and endtime defined.
			$interval = ($endTime - $startTime) / 500;
		}
	}
	if ($interval == "0") {
		//value of 0 indicates user wants all data points to be sent.
		return "";
	}

	$rowsToExtract = (($tableEndTime - $tableStartTime + $interval) / $interval);
	$extractEvery = $numRows / $rowsToExtract;
	if ($extractEvery < 1) {
		//this will mess sql modulus function up since only deals with ints. so would get mod 0. =error.
		return "";
	}
	//multiplying modulus stuff by 16 gives
	$condition = "(((rowid * 16) % (" . $extractEvery . "*16))/16 < 0.5 OR " . $extractEvery . " - (((16*rowid) % (16*" . $extractEvery . "))/16) < 0.5)";
	return $condition;
	//works.
}

function setUpChannelArray()
{
	$channelStr = $_POST['channels'];
	$chanArray = [];
	if ($channelStr == "ALL") {
		return $chanArray;
		//by returning array this does not mess up other functions.
	}
	$chanArray = explode("<P1>", $channelStr);
	//now should have $chanArray which is an array containing the IDs of each channel to be retrieved.
	return $chanArray;
}

function findColsToSelect($tableName, &$db, $chanArray)
{

	$sqlString = "PRAGMA table_info('" . $tableName . "');";
	$results = @queryResultSQL($sqlString, 5000, $db);
	if ($results == false) {
		echo "1";
		writeToErrorLog("Server database access error", 12);
		$db->close();
		die();
	}
	$returnStr = "";
	$row = $results->fetchArray(SQLITE3_ASSOC);
	$chanArrayLen = count($chanArray);
	while ($row != false) {
		for ($i = 0; $i < $chanArrayLen; $i++) {
			if ($row['name'] == $chanArray[$i]) {
				//channel in table should be monitored and so is added to return string.
				if ($returnStr == "") {
					$returnStr .= "[" . $chanArray[$i] . "]";
				} else {
					$returnStr .= ",[" . $chanArray[$i] . "]";
				}
				break;
			}
		}
		$row = $results->fetchArray(SQLITE3_ASSOC);
	}
	//now have a return string which contains a list of comma separated channel names to be retrieved from the table.
	return $returnStr;
}

//unprogrammed, unused function.
function exportCSV(&$arrayOfLoggers)
{
	//go through each row for each loggers output
	//export each loggeroutput row with tab in between

	//the output string:
	$output = true; //boolean representing if any channel outputted data. if == false then loop ends.

	//for each row:
	$row = 0;
	while ($output == true) {
		$output = false;

		//for each channel.
		$first = true;
		foreach ($arrayOfLoggers as $key1 => $value1) {
			foreach ($arrayOfLoggers[$key1] as $key2 => $value2) {
				if (isset($arrayOfLoggers[$key1][$key2][$row]) || array_key_exists($row, $arrayOfLoggers[$key1][$key2])) {
					$output = true;
					if ($first == true) {
						$first = false;
					} else {
						echo ",";
					}
					//output time and value.
					echo $arrayOfLoggers[$key1][$key2][$row][0] . "," . $arrayOfLoggers[$key1][$key2][$row][1];
				}
			}
		}
	}
}

function executeSQL($sqlString, $msTimeout, &$db)
{
	$time_start = microtime(true);
	while (((microtime(true) - $time_start) * 1000) < $msTimeout) {
		if ($db->exec($sqlString) == true) {
			return true;
		} else {
			//wait 1 ms
			usleep(1000);
		}
	}
	return false;
}
function queryRowSQL($sqlString, $msTimeout, &$db)
{
	$time_start = microtime(true);
	$i = 0;
	while (((microtime(true) - $time_start) * 1000) < $msTimeout) {
		$results = $db->query($sqlString);
		if ($results != false) {
			$returnRow = $results->fetchArray(SQLITE3_ASSOC);
			if ($returnRow != false) {
				return $returnRow;
			}
		}
		//wait 1 ms
		usleep(1000);
	}
	return false;
}
function queryResultSQL($sqlString, $msTimeout, &$db)
{
	$time_start = microtime(true);
	$i = 0;
	while (((microtime(true) - $time_start) * 1000) < $msTimeout) {
		$results = $db->query($sqlString);
		if ($results != false) {
			return $results;
		}
		//wait 1 ms
		usleep(1000);
	}
	return false;
}
function writeToErrorLog($str, $errNumber)
{
	$errorLog = @fopen("../Error_log.txt", "a");
	if ($errorLog != false) {
		fwrite($errorLog, "\n" . date("D M d H:i:s Y") . "\nPhp" . $errNumber . "-" . $str);
		fclose($errorLog);
	}
}

?>
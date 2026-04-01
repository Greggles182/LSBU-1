<?php
$db = new SQLite3('../Logging database.db');
$returnRow = @queryRowSQL("SELECT Status FROM ConfigTable;", 1000, $db);
if ($returnRow != false) {
  $status = $returnRow['Status'];
  echo $status;
} else {
  writeToErrorLog("Server database access error", 1);
}
$db->close();
return;

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

function writeToErrorLog($str, $errNumber)
{
  $errorLog = @fopen("../Error_log.txt", "a");
  if ($errorLog != false) {
    fwrite($errorLog, "\n" . date("D M d H:i:s Y") . "\nPhp" . $errNumber . "-" . $str);
    fclose($errorLog);
  }
}
?>
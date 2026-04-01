<?php
$postString = $_POST['command'];

// Switch statement to handle different commands
switch ($postString) {

  case "BACKUP":
    $time_start = microtime(true);
    $msTimeout = 5000; // Timeout in milliseconds

    // Try copying the database to a backup file within the timeout period
    while (((microtime(true) - $time_start) * 1000) < $msTimeout) {
      if (copy("../Logging database.db", "../backup.db") == true) {
        echo "Internal backup updated successfully.";
        return;
      }
      usleep(1000); // Wait 1 ms before retrying
    }

    // If here, all attempts to back up the database failed
    writeToErrorLog("Failed to update internal backup.", 7);
    echo "Failed to update internal backup.";
    return;

  case "RESTORE":
    // Check if the backup file exists
    if (!file_exists("../backup.db")) {
      writeToErrorLog("Failed to restore database - backup file does not exist.", 8);
      echo "Backup file does not exist.";
      return;
    }

    $time_start = microtime(true);
    $msTimeout = 5000; // Timeout in milliseconds

    // Try restoring the backup within the timeout period
    while (((microtime(true) - $time_start) * 1000) < $msTimeout) {
      if (copy("../backup.db", "../Logging database.db") == true) {
        echo "Database backup restored successfully.";
        return;
      }
      usleep(1000); // Wait 1 ms before retrying
    }

    // If here, all attempts to restore the database backup failed
    writeToErrorLog("Failed to restore internal database backup.", 9);
    echo "Failed to restore internal database backup.";
    return;

  case "CLEARERRORLOG":
    $time_start = microtime(true);
    $msTimeout = 5000; // Timeout in milliseconds

    // Try opening the error log file in write mode to clear it
    while (((microtime(true) - $time_start) * 1000) < $msTimeout) {
      $errorLog = @fopen("../Error_log.txt", "w");
      if ($errorLog != false) {
        fwrite($errorLog, "Cleared: " . date("D M d H:i:s Y") . "\n");
        fclose($errorLog);
        echo "Error log cleared.";
        return;
      }
      usleep(1000); // Wait 1 ms before retrying
    }

    // If here, all attempts to clear the error log failed
    writeToErrorLog("Error clearing error log!", 10);
    echo "Error clearing error log!";
    return;

  default:
    // Handle invalid commands
    echo "Invalid command.";
    return;
}

// Function to log errors to the error log file
function writeToErrorLog($str, $errNumber) {
  $errorLog = @fopen("../Error_log.txt", "a");
  if ($errorLog != false) {
    fwrite($errorLog, "\n" . date("D M d H:i:s Y") . "\nPhp" . $errNumber . "-" . $str);
    fclose($errorLog);
  }
}
?>

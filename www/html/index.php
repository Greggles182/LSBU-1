<?php
try {
    $jsonData = file_get_contents('/var/www/html/data.json');

    // Check if file reading was successful
    if ($jsonData === false) {
        die("Error reading JSON file.");
    }

    // Decode JSON to an array (optional)
    $dataArray = json_decode($jsonData, true);
    // Set the default timezone (adjust as needed; use 'UTC' if your timestamps are UTC)
    date_default_timezone_set('UTC');

    // Configuration
    $dbPath = '/var/www/html/example.db'; // Path to SQLite database
    $tableName = $dataArray['dbTable']; // Table name

    // Connect to SQLite
    $pdo = new PDO("sqlite:$dbPath");
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Determine date range.
    // If GET parameters 'start' and 'end' are not provided, fetch the full range from the table.
    if (!isset($_GET['start']) || !isset($_GET['end'])) {
        $rangeQuery = $pdo->query("SELECT MIN(TIMESTAMP) as min_ts, MAX(TIMESTAMP) as max_ts FROM $tableName");
        $range = $rangeQuery->fetch(PDO::FETCH_ASSOC);
        if ($range && $range['min_ts'] !== null && $range['max_ts'] !== null) {
            $start = $range['min_ts']; // already in milliseconds
            $end   = $range['max_ts'];
        } else {
            // Fallback: last 1 hour if no data
            $end = time() * 1000; 
            $start = $end - (3600 * 1000);
        }
    } else {
        // Convert the datetime-local string to Unix timestamp (seconds) then to milliseconds
        $start = strtotime($_GET['start']) * 1000;
        $end   = strtotime($_GET['end']) * 1000;
    }


    if (isset($_GET['export'])) {
        header('Content-Type: text/csv');
        header('Content-Disposition: attachment; filename="data.csv"');

        $csvQuery = $pdo->prepare("SELECT * FROM $tableName WHERE TIMESTAMP BETWEEN :start AND :end ORDER BY TIMESTAMP ASC");
        $csvQuery->execute([':start' => $start, ':end' => $end]);
        $csvData = $csvQuery->fetchAll(PDO::FETCH_ASSOC);

        $output = fopen('php://output', 'w');
        if (count($csvData) > 0) {
            fputcsv($output, array_keys($csvData[0])); // CSV Header
        }
        foreach ($csvData as $row) {
            // Ensure TIMESTAMP is exported with full precision and not in scientific notation.
            if (isset($row['TIMESTAMP'])) {
                // If TIMESTAMP is numeric, format as a non-scientific integer string.
                if (is_numeric($row['TIMESTAMP'])) {
                    // '%.0f' preserves integer precision even if value was returned as float.
                    $row['TIMESTAMP'] = sprintf('%.0f', $row['TIMESTAMP']);
                } else {
                    $row['TIMESTAMP'] = (string)$row['TIMESTAMP'];
                }
            }
            fputcsv($output, $row);
        }
        fclose($output);
        exit;
    }

    // Fetch Data for Graph based on date range
    $query = $pdo->prepare("SELECT * FROM $tableName WHERE TIMESTAMP BETWEEN :start AND :end ORDER BY TIMESTAMP ASC");
    $query->execute([':start' => $start, ':end' => $end]);
    $data = $query->fetchAll(PDO::FETCH_ASSOC);

    // Convert Data for JavaScript
    $jsonData = json_encode($data, JSON_NUMERIC_CHECK);
} catch (Exception $e) {
    // Handle any errors that occur during the database connection or query execution
    error_log("Error: " . $e->getMessage());
    $jsonData = json_encode([]);
    // Optionally, you can display an error message to the user
    //echo "<p>Error fetching data: " . htmlspecialchars($e->getMessage()) . "</p>";
    //exit;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
    <link rel="manifest" href="/site.webmanifest">
    <title>Recorded Data</title>
    <link rel="stylesheet" href="styles.css">
    <script src="chart.js"></script>
</head>
<body>
     <!-- <h2>Recorded Data</h2> -->
    
    <!-- Date Range Selection -->
    <div class="controls">
        <div class="date-range">
            <label for="start">Start Date:</label>
            <input type="datetime-local" id="start" name="start" value="<?php echo date('Y-m-d\TH:i', $start/1000); ?>">
            <label for="end">End Date:</label>
            <input type="datetime-local" id="end" name="end" value="<?php echo date('Y-m-d\TH:i', $end/1000); ?>">
            <button onclick="updateRange()">Update Range</button>
            <button onclick="resetRange()">Reset Range</button>
        </div>
        <div class="actions">
            <button onclick="downloadCSV()">Download CSV of current data range</button>
            <a href="export.html"><button type="button">Other export options</button></a>
            <a href="config.html"><button type="button">Configure</button></a>
        </div>
    </div>

    <!-- Graph Canvas -->
    <canvas id="dataChart"></canvas>

    <script>
        function showNotification(message, type) {
            const notification = document.createElement('div');
            notification.classList.add('notification', type);
            notification.textContent = message;
            document.body.appendChild(notification);

            // Remove the notification after 3 seconds
            setTimeout(() => {
                notification.classList.add('hide');
                setTimeout(() => {
                    notification.remove();
                }, 500); // Wait for fade-out animation before removing
            }, 3000); // Duration the message will be visible
        }
        // Parse the data from PHP
        let rawData = <?= $jsonData ?>;
        console.log("Raw data:", rawData);

        // If no data is returned, display a message in the console
        if (rawData.length === 0) {
            console.warn("No data found for the selected date range.");
            showNotification("No data found for the selected date range.", 'error');
        }

        // Map timestamps to labels (timestamps are already in milliseconds)
        let labels = rawData.map(row => {
            let timestamp = Number(row.TIMESTAMP);
            let date = new Date(timestamp);
            if (isNaN(date.getTime())) {
                console.error("Invalid date:", row.TIMESTAMP);
                showNotification(`Invalid date: ${row.TIMESTAMP}`, 'error');
                return "Invalid Date";
            }
            return date.toLocaleString();
        });

        let datasets = [];
        // Define Graph Data (skip TIMESTAMP and ID columns)
        let columns = Object.keys(rawData[0] || {}).filter(col => col !== "TIMESTAMP" && col !== "ID");
        columns.forEach((col, i) => {
            datasets.push({
                label: col,
                data: rawData.map(row => row[col]),
                borderColor: `hsl(${i * 40}, 70%, 50%)`,
                backgroundColor: `hsl(${i * 40}, 70%, 70%)`,
                hidden: false,
                fill: false
            });
        });

        // Only create the chart if there is data
        if (rawData.length > 0) {
            let ctx = document.getElementById("dataChart").getContext("2d");
            let dataChart = new Chart(ctx, {
                type: "line",  // Ensuring it's a line chart
                data: { labels, datasets },
                options: {
                    responsive: true,
                    spanGaps: true,
                    scales: {
                        x: { 
                            title: { display: true, text: "Timestamp", color: "#ffffff", font: { size: 14 } },
                            ticks: { color: "#ffffff", font: { size: 12 } }
                        },
                        y: { 
                            title: { display: true, text: "Value", color: "#ffffff", font: { size: 14 } },
                            ticks: { color: "#ffffff", font: { size: 12 } }
                        }
                    },
                    elements: {
                        line: { tension: 0.2 }  // Adjusting for smoother lines
                    },
                    plugins: {
                        legend: {
                            display: true,
                            labels: {
                                color: "#ffffff", // White text for the legend
                                font: { size: 14 }
                            },
                            onClick: (e, legendItem) => {
                                let index = legendItem.datasetIndex;
                                let meta = dataChart.getDatasetMeta(index);
                                meta.hidden = meta.hidden === null ? true : null;
                                dataChart.update();
                            }
                        }
                    }
                }
            });
        }// } else {
        //     document.getElementById("dataChart").style.display = "none";
        //     let msg = document.createElement("p");
        //     msg.textContent = "No data found for the selected date range.";
        //     document.body.appendChild(msg);
        // }

        // Reload page with selected start and end dates
        function updateRange() {
            let start = document.getElementById("start").value;
            let end = document.getElementById("end").value;
            window.location.href = `?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
        }

        // CSV export including date range parameters
        function downloadCSV() {
            let start = document.getElementById("start").value;
            let end = document.getElementById("end").value;
            window.location.href = `?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&export=1`;
        }
        function resetRange() {
            const currentHostname = window.location.hostname;
            window.location.href = `http://${currentHostname}/`;
        }
    </script>
</body>
</html>

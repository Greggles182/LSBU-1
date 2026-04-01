#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <FS.h>
#include <LittleFS.h>

WiFiClient client;

const char* ssid = "LOG-1";
const char* passwd = "12345678";
const int lightSensor = 12;

void setup() {
  Serial.begin(74880);
  Serial.println("\n");
  WiFi.mode(WIFI_OFF);
  WiFi.forceSleepBegin();
  delay(1);

  pinMode(lightSensor, INPUT);

  //Execute non-Wifi code here
  if (digitalRead(lightSensor) == 1) {
    Serial.println("You too fast boy");
  }
  while (digitalRead(lightSensor) == 0) {
    delay(10);
  }
  int closes = millis();

  WiFi.forceSleepWake();
  delay(1);
  WiFi.persistent(false);
  Serial.printf("Connecting to %s\n", ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, passwd);

  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED) {
    timeout++;
    delay(500);
    Serial.print(".");
    if (timeout == 60) {
      Serial.println("Failed to connect to wifi!");
      GoSleep();
      return;
    }
  }
  Serial.println(" Connected");
  Serial.print("ESP IP: ");
  Serial.println(WiFi.localIP());

  HTTPClient http;
  http.begin(client, "http://192.168.5.1:8000/Lidata");
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  String postData = "data=" + String(closes / 1000);
  Serial.println(postData);
  int httpResponseCode = http.POST(postData);
  Serial.println("Response: " + String(httpResponseCode));

  if (httpResponseCode != 200 && httpResponseCode != 419) {
    Serial.println("Retry...");
    Serial.println(postData);
    httpResponseCode = http.POST(postData);
    Serial.println("Response: " + String(httpResponseCode));
    if (httpResponseCode != 200 && httpResponseCode != 419) {
      Serial.println("Failed!");
    }
  }
  if (httpResponseCode == 419) {
    ESP.deepSleep(0, WAKE_RF_DISABLED);
  }
  http.end();

  WiFi.disconnect(true);
  delay(1);
  WiFi.mode(WIFI_OFF);
  WiFi.forceSleepBegin();
  delay(1);

  GoSleep();
}

void GoSleep() {
  ESP.deepSleep(0, WAKE_RF_DISABLED);
}

void loop() {
  GoSleep();
}

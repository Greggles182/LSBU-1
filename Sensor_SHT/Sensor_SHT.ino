#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <Wire.h>
#include "SHT31.h"
#include <FS.h>
#include <LittleFS.h>

#define SHT31_ADDRESS   0x44
#define CONFIG_FILE "/config.txt"

IPAddress staticIP(192,168,5,255);
IPAddress gateway(192,168,5,1);
IPAddress subnet(255,255,255,0);

SHT31 sht;
WiFiClient client;

String ssid;
String passwd;
int id;
unsigned long sleepTime;
const int sleepy = 13;
bool DoSleep;

void setup() {
  Serial.begin(74880);
  WiFi.mode(WIFI_OFF);
  WiFi.forceSleepBegin();
  delay(1);
  pinMode(sleepy, INPUT_PULLUP);
  Serial.println(digitalRead(sleepy));
  DoSleep = digitalRead(sleepy);
  if (!LittleFS.begin()) {
    Serial.println("LittleFS Mount Failed");
    GoSleep();
    return;
  }
  if (DoSleep) {
    return;
  }
  File file = LittleFS.open(CONFIG_FILE, "r");
  if (!file) { 
    Serial.println("Failed to open config file!"); 
    GoSleep();
    return; 
  }
  
  String content = file.readString();
  file.close();

  int idx1 = content.indexOf('\n');
  int idx2 = content.indexOf('\n', idx1 + 1);
  int idx3 = content.indexOf('\n', idx2 + 1);
  int idx4 = content.indexOf('\n', idx3 + 1);

  if (idx1 == -1 || idx2 == -1 || idx3 == -1 || idx4 == -1) return;

  id = content.substring(0, idx1).toInt();
  sleepTime = content.substring(idx1 + 1, idx2).toInt();
  ssid = content.substring(idx2 + 1, idx3);
  passwd = content.substring(idx3 + 1, idx4);

  Serial.println(id);
  Serial.println(sleepTime);
  Serial.println(ssid);
  Serial.println(passwd);

  if (id + 1 >= 253) {
    Serial.println("Invalid static IP configuration!");
    GoSleep();
    return;
  }
  staticIP[3] = id + 1;

  Wire.begin(4, 5);
  Wire.setClock(100000);
  sht.begin();

  if (!sht.read()) {
    Serial.println("SHT31 read failed!");
    GoSleep();
    return;
  }

  WiFi.forceSleepWake();
  delay(1);
  WiFi.persistent(false);
  Serial.printf("Connecting to %s\n", ssid.c_str());
  Serial.println(staticIP);
  WiFi.config(staticIP, gateway, subnet);
  WiFi.begin(ssid.c_str(), passwd.c_str());

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
  http.begin(client, "http://192.168.5.1:8000/data");
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  String postData = "data=" + String(id) + ", " + String(sht.getTemperature()) + ", " + String(sht.getHumidity());
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
    ESP.deepSleep(0);
  }
  http.end();

  WiFi.disconnect(true);
  delay(1);
  WiFi.mode(WIFI_OFF);
  WiFi.forceSleepBegin();
  delay(1);

  // if (!(digitalRead(sleepy) == HIGH)) {
  //   if (httpResponseCode == 419) {
  //     ESP.deepSleep(0);
  //   }
  //   if ((millis() * 1000) < (sleepTime * 1000000)) {
  //     ESP.deepSleep((sleepTime * 1000000) - (millis() * 1000), WAKE_RF_DISABLED);
  //   } else {
  //     ESP.deepSleep(1000000, WAKE_RF_DISABLED);
  //   }
  // }
  GoSleep();
}

void GoSleep() {
  if (!DoSleep) {
    if ((millis() * 1000) < (sleepTime * 1000000)) {
      ESP.deepSleep((sleepTime * 1000000) - (millis() * 1000));
    } else {
      ESP.deepSleep(1000000);  // Sleep for 1 second if already over
    }
  }
  else {
    return;
  }
}

void saveConfig(int newId, unsigned long newSleepTime, String newSsid, String newPasswd) {
  id = newId;
  sleepTime = (newSleepTime > 3600) ? 3600 : newSleepTime; // Limit sleep time to 1 hour max
  ssid = newSsid;
  passwd = newPasswd;
  
  File file = LittleFS.open(CONFIG_FILE, "w");
  if (!file) return;
  file.printf("%i\n%lu\n%s\n%s\n", id, sleepTime, ssid.c_str(), passwd.c_str());
  file.close();
}

bool Messaged = false;
void loop() {
  if (Messaged == false) {
    Serial.println("Entered config setup.");
    Messaged = true;
  }
  if (Serial.available()) {
    String input = Serial.readString();
    input.trim(); // Remove whitespace
    if (input.startsWith("SET")) {
      int spaceIndex1 = input.indexOf(' ', 4);
      int spaceIndex2 = input.indexOf(' ', spaceIndex1 + 1);
      int spaceIndex3 = input.indexOf(' ', spaceIndex2 + 1);
      
      id = input.substring(4, spaceIndex1).toInt();
      sleepTime = input.substring(spaceIndex1 + 1, spaceIndex2).toInt();
      ssid = input.substring(spaceIndex2 + 1, spaceIndex3);
      passwd = input.substring(spaceIndex3 + 1);
      
      saveConfig(id, sleepTime, ssid, passwd);
      Serial.println("Configuration saved. Restarting...");
      delay(500);
      ESP.restart();
    }
  }
}

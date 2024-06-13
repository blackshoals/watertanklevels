//V3 - use buttons to call sensor readings

#include <esp_now.h>
#include <WiFi.h>
#include <TFT_eSPI.h>
#include <ArduinoJson.h>
#include "NotoSmall.h"
#include "Noto.h"
#include "NotoBig.h"
#include <ArduinoJson.h>

#define PIN_POWER_ON 15    //enable battery
TFT_eSPI tft = TFT_eSPI();
TFT_eSprite sprite = TFT_eSprite(&tft);

int x=85;
int y=100;
int upper_tank_percentage=0; // show empty until a sensor reading comes in
int lower_tank_percentage=0;
int battery_voltage=0;
unsigned short c1=TFT_BLUE;
unsigned short c2=TFT_BLACK;
unsigned short c3=TFT_WHITE;
unsigned short c4=TFT_SILVER;
unsigned short c5=TFT_GREEN;
unsigned short c6=TFT_YELLOW;
unsigned short c7=TFT_RED;
unsigned short upper_tank_arc_colour;
unsigned short lower_tank_arc_colour;

unsigned long startTime = millis(); // Store the current time
String data;
String sensorcall = "get_readings";

uint8_t pumpcontrollermac[] = {0xB0, 0xB2, 0x1C, 0x50, 0xB2, 0xB0};
esp_now_peer_info_t peerInfo;

void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {

// Convert the incoming byte array to a string
  data = String((char*)incomingData);
  
  // Allocate memory for the JSON document
  StaticJsonDocument<250> doc; // Adjust the size based on your expected JSON structure

  // Deserialize the JSON string into the document
  DeserializationError error = deserializeJson(doc, data);


  // Access the values from the parsed JSON
  upper_tank_percentage = doc["upper_tank_percentage"].as<int>();
  lower_tank_percentage = doc["lower_tank_percentage"].as<int>(); // Make sure this key exists in your JSON
  battery_voltage = doc["battery_voltage"].as<int>(); // Ensure this key matches your JSON structure
  
  draw(); //draw the gauges
}

void setup() {

  //Serial.begin(9600);

  pinMode(PIN_POWER_ON, OUTPUT);   //triggers the LCD backlight, and enables battery power
  digitalWrite(PIN_POWER_ON, HIGH);  //enable battery power

  pinMode(0,INPUT_PULLUP); //activate the 2 front buttons on the T-Display
  pinMode(14,INPUT_PULLUP);
  
  tft.init();
  tft.fillScreen(c2);
  //tft.drawString("WAITING...",10,10,4);

  tft.setRotation(3);
    // Set text attributes
  tft.setTextColor(TFT_WHITE); // Set text color to white
  tft.setTextSize(2); // Set text size to 15 (size 1 corresponds to 15px font size in TFT_eSPI)
  
  // Print the welcome message
  tft.setCursor(0, 10); // Position the cursor where the text should start
  tft.println("Press either button to");
  tft.println("read the sensors.");
  tft.println();
  tft.println("The display will sleep");
  tft.println("after 5 min.");

  tft.setRotation(0);
  sprite.createSprite(170,320);

     //brightness
     ledcSetup(0, 10000, 8);
     ledcAttachPin(38, 0);
     ledcWrite(0, 160);


  WiFi.mode(WIFI_STA);
  esp_now_init();
  esp_now_register_recv_cb(OnDataRecv); // Call OnDataRecv to process the message when it comes in

  // Register Pumpcontroller peer
  memcpy(peerInfo.peer_addr, pumpcontrollermac, 6);
  peerInfo.channel = 0;  
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

}

void draw()
  {

    if (upper_tank_percentage >= 60) {
        upper_tank_arc_colour = c5;
    } else if ((upper_tank_percentage < 60) && (upper_tank_percentage >= 30)) {
        upper_tank_arc_colour = c6;
    }
      else {
        upper_tank_arc_colour = c7;
    }
  
     if (lower_tank_percentage >= 60) {
        lower_tank_arc_colour = c5;
    } else if ((lower_tank_percentage < 60) && (lower_tank_percentage >= 30)) {
        lower_tank_arc_colour = c6;
    }
      else {
        lower_tank_arc_colour = c7;
    }  

//Header Label
    sprite.loadFont(Noto);
    sprite.setTextDatum(0);
    sprite.setTextColor(c4,c2);
    sprite.drawString("Water Levels",x-45,6);
    sprite.unloadFont();

//Upper Tank
    sprite.loadFont(Noto);
    sprite.setTextDatum(0);
    sprite.setTextColor(c4,c2);
    sprite.drawString("Upper Tank %",x-50,y-70);
    sprite.unloadFont();

    sprite.drawSmoothArc(x, y, 50, 35, 0, (upper_tank_percentage*360)/100, upper_tank_arc_colour,c2);
    sprite.drawSmoothArc(x, y, 50, 35, (upper_tank_percentage*360)/100, 360, 0x09CB, c2);

    sprite.loadFont(NotoBig);
    sprite.setTextDatum(4);
    sprite.setTextColor(c3,c2,true);
    sprite.drawNumber(upper_tank_percentage,x,y);
    sprite.unloadFont();

//Lower Tank
    sprite.loadFont(Noto);
    sprite.setTextDatum(0);
    sprite.setTextColor(c4,c2);
    sprite.drawString("Lower Tank %",x-50,y+65);
    sprite.unloadFont();

    sprite.drawSmoothArc(x, y+135, 50,35, 0, (lower_tank_percentage*360)/100, lower_tank_arc_colour, c2);
    sprite.drawSmoothArc(x, y+135, 50,35, (lower_tank_percentage*360)/100, 360, 0x09CB, c2);

    sprite.loadFont(NotoBig);
    sprite.setTextDatum(4);
    sprite.setTextColor(c3,c2,true);
    sprite.drawNumber(lower_tank_percentage,x,y+135);
    sprite.unloadFont();

// Sensor Battery
    sprite.loadFont(NotoSmall);
    sprite.setTextDatum(0);
    sprite.setTextColor(c4,c2);
    sprite.drawString("Sensor Battery %",x-60,y+200);
    sprite.unloadFont();

    sprite.loadFont(NotoSmall);
    sprite.setTextDatum(4);
    sprite.setTextColor(c3,c2,true);
    sprite.drawNumber(battery_voltage,x+50,y+205);
    sprite.unloadFont();
    
// Draw the display  
    sprite.pushSprite(0,0);
  }

void sendMessageAndWait(String message, unsigned long timeout) {
  static unsigned long lastSendTime = 0;
  static bool sentMessage = false;

  if (!sentMessage || millis() - lastSendTime > timeout) {
    esp_now_send(pumpcontrollermac, (uint8_t *)message.c_str(), message.length());
    sentMessage = true;
    lastSendTime = millis();
  }
}

void sleepDisplay() {
    //Now sleep the display
    pinMode(4,OUTPUT); //
    digitalWrite(4,LOW); // Should force backlight off
    tft.writecommand(ST7789_DISPOFF);// Switch off the display
    tft.writecommand(ST7789_SLPIN);// Sleep the display driver  
}

void loop() {

  if(digitalRead(0)==0||digitalRead(14)==0)
  {
    sendMessageAndWait("get_readings", 5000); // Send message every 5 seconds
  }  
   
  if (millis() - startTime >= 300000) // If 5 minutes has passed or the right button pressed begin sleep
  { 
    
    //Now sleep the display

    sleepDisplay();

    // Put the ESP32 into deep sleep mode
    esp_deep_sleep_start(); // Enter deep sleep mode
  }
  
}

//V2 - add battery sensor label and change fonts

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

void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {

// Convert the incoming byte array to a string
  data = String((char*)incomingData);

  // Allocate memory for the JSON document
  StaticJsonDocument<250> doc; // Adjust the size based on your expected JSON structure

  // Deserialize the JSON string into the document
  DeserializationError error = deserializeJson(doc, data);

//  // Check if the deserialization was successful
//  if (error) {
//    Serial.print(F("deserializeJson() failed: "));
//    Serial.println(error.f_str());
//    return;
//  }

  // Access the values from the parsed JSON
  upper_tank_percentage = doc["upper_tank_percentage"].as<int>();
  lower_tank_percentage = doc["lower_tank_percentage"].as<int>(); // Make sure this key exists in your JSON
  battery_voltage = doc["battery_voltage"].as<int>(); // Ensure this key matches your JSON structure

//  Serial.print("Upper Tank Percentage:");
//  Serial.println(upper_tank_percentage);
//  Serial.print("Lower Tank Percentage:");
//  Serial.println(lower_tank_percentage);
//  Serial.print("Battery Voltage:");
//  Serial.println(battery_voltage);
  
  draw(); //draw the gauges
}

void setup() {

  //Serial.begin(9600);

  pinMode(PIN_POWER_ON, OUTPUT);   //triggers the LCD backlight, and enables battery power
  digitalWrite(PIN_POWER_ON, HIGH);  //enable battery power
  
  tft.init();
  tft.fillScreen(c2);
  tft.drawString("Waiting for",10,40,4);
  tft.drawString("sensor data.",10,70,4);
  sprite.createSprite(170,320);

     //brightness
     ledcSetup(0, 10000, 8);
     ledcAttachPin(38, 0);
     ledcWrite(0, 160);


  WiFi.mode(WIFI_STA);
  esp_now_init();
  esp_now_register_recv_cb(OnDataRecv); // Call OnDataRecv to process the message when it comes in
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

    sprite.drawSmoothArc(x, y+5, 50, 35, 0, (upper_tank_percentage*360)/100, upper_tank_arc_colour,c2);
    sprite.drawSmoothArc(x, y+5, 50, 35, (upper_tank_percentage*360)/100, 360, 0x09CB, c2);

    sprite.loadFont(NotoBig);
    sprite.setTextDatum(4);
    sprite.setTextColor(c3,c2,true);
    sprite.drawNumber(upper_tank_percentage,x,y+5);
    sprite.unloadFont();

//Lower Tank
    sprite.loadFont(Noto);
    sprite.setTextDatum(0);
    sprite.setTextColor(c4,c2);
    sprite.drawString("Lower Tank %",x-50,y+70);
    sprite.unloadFont();

    sprite.drawSmoothArc(x, y+144, 50,35, 0, (lower_tank_percentage*360)/100, lower_tank_arc_colour, c2);
    sprite.drawSmoothArc(x, y+144, 50,35, (lower_tank_percentage*360)/100, 360, 0x09CB, c2);

    sprite.loadFont(NotoBig);
    sprite.setTextDatum(4);
    sprite.setTextColor(c3,c2,true);
    sprite.drawNumber(lower_tank_percentage,x,y+146);
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


void loop() {

  
  if (millis() - startTime >= 300000) { // If 5 minutes has passed begin sleep
    
    //Now sleep the display
    pinMode(4,OUTPUT); //
    digitalWrite(4,LOW); // Should force backlight off
    tft.writecommand(ST7789_DISPOFF);// Switch off the display
    tft.writecommand(ST7789_SLPIN);// Sleep the display driver

    // Put the ESP32 into deep sleep mode
    //esp_sleep_enable_timer_wakeup(1 * 20 * 1000000); // Set wakeup timer for 20 seconds
    esp_deep_sleep_start(); // Enter deep sleep mode
  }
  
}

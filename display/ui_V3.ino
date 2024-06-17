#include <lvgl.h>
#include <ui.h>
#include <esp_now.h>
#include <WiFi.h>
#include <ArduinoJson.h>

#include <TFT_eSPI.h>
TFT_eSPI tft = TFT_eSPI(); /* TFT instance */

#define PIN_POWER_ON 15    //enable battery

/*Don't forget to set Sketchbook location in File/Preferences to the path of your UI project (the parent foder of this INO file)*/
//mac of the controller
uint8_t receiverAdd[] = {0xB0, 0xB2, 0x1C, 0x50, 0xB2, 0xB0};
esp_now_peer_info_t peerInfo;

int upper_tank_percentage=0; // show empty until a sensor reading comes in
int lower_tank_percentage=0;
int battery_voltage=0;
int sensor_signal=0;
bool pump_auto_flag;
bool pump_state;

typedef struct struct_message {
  int lower_tank_percentage;
  int upper_tank_percentage;
  int battery_voltage;
  int sensor_signal;
  bool pump_auto_flag;
  bool pump_state;
} struct_message;

struct_message sensorData;

String sta;
String lowerPcttext;
String upperPcttext;
String sensorCall = "get_sensors";
String autoOn = "auto_on";
String autoOff = "auto_off";
String pumpOn = "pump_on";
String pumpOff = "pump_off";

unsigned long startTime = millis(); // Store the current time

//these are needed to debounce the pins on 0 and 14
const int inputPin0 = 0; // First button connected to Pin 0
const int inputPin14 = 14; // Second button connected to Pin 14

int buttonState0 = 0;
int currentButtonState0 = HIGH; // Assume initially open
int lastButtonState0 = HIGH; // Last known state of button 0
unsigned long lastDebounceTime0 = 0; // Last time the output pin was toggled
bool toggleState0 = false; // Variable to keep track of the toggle state for Pin 14

int buttonState14 = 0;
int currentButtonState14 = HIGH; // Assume initially open
int lastButtonState14 = HIGH; // Last known state of button 1
unsigned long lastDebounceTime14 = 0; // Last time the output pin was toggled
bool toggleState14 = false; // Variable to keep track of the toggle state for Pin 14

long debounceDelay = 50; // Debounce delay in milliseconds

/*Change to your screen resolution*/
static const uint16_t screenWidth  = 170;
static const uint16_t screenHeight = 320;

static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf[ screenWidth * screenHeight / 10 ];



#if LV_USE_LOG != 0
/* Serial debugging */
void my_print(const char * buf)
{
    Serial.printf(buf);
    Serial.flush();
}
#endif

/* Display flushing */
void my_disp_flush( lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p )
{
    uint32_t w = ( area->x2 - area->x1 + 1 );
    uint32_t h = ( area->y2 - area->y1 + 1 );

    tft.startWrite();
    tft.setAddrWindow( area->x1, area->y1, w, h );
    tft.pushColors( ( uint16_t * )&color_p->full, w * h, true );
    tft.endWrite();

    lv_disp_flush_ready( disp );
}

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status)
{
  if(status == ESP_NOW_SEND_SUCCESS) 
  sta="Delivery Success"; else sta="Delivery Fail";
}


void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len)
{

  memcpy(&sensorData, incomingData, sizeof(sensorData));
  lower_tank_percentage = sensorData.lower_tank_percentage;
  upper_tank_percentage = sensorData.upper_tank_percentage;
  battery_voltage = sensorData.battery_voltage;
  sensor_signal = sensorData.sensor_signal;
  pump_auto_flag = sensorData.pump_auto_flag;
  pump_state = sensorData.pump_state; 

  drawData();
}

void setup()
{
    Serial.begin( 115200 ); /* prepare for possible serial debug */

    pinMode(PIN_POWER_ON, OUTPUT);   //triggers the LCD backlight, and enables battery power
    digitalWrite(PIN_POWER_ON, HIGH);  //enable battery power

    pinMode(0,INPUT_PULLUP); //activate the 2 front buttons on the T-Display
    pinMode(14,INPUT_PULLUP);
    
    String LVGL_Arduino = "Hello Arduino! ";
    LVGL_Arduino += String('V') + lv_version_major() + "." + lv_version_minor() + "." + lv_version_patch();

    Serial.println( LVGL_Arduino );
    Serial.println( "I am LVGL_Arduino" );

    lv_init();

#if LV_USE_LOG != 0
    lv_log_register_print_cb( my_print ); /* register print function for debugging */
#endif

    tft.begin();          /* TFT init */
    tft.setRotation( 0 ); /* Landscape orientation, flipped */

    lv_disp_draw_buf_init( &draw_buf, buf, NULL, screenWidth * screenHeight / 10 );

    /*Initialize the display*/
    static lv_disp_drv_t disp_drv;
    lv_disp_drv_init( &disp_drv );
    /*Change the following line to your display resolution*/
    disp_drv.hor_res = screenWidth;
    disp_drv.ver_res = screenHeight;
    disp_drv.flush_cb = my_disp_flush;
    disp_drv.draw_buf = &draw_buf;
    lv_disp_drv_register( &disp_drv );

    /*Initialize the (dummy) input device driver*/
    static lv_indev_drv_t indev_drv;
    lv_indev_drv_init( &indev_drv );
    indev_drv.type = LV_INDEV_TYPE_POINTER;
    lv_indev_drv_register( &indev_drv );

    ui_init();
  
    WiFi.mode(WIFI_STA);
    esp_now_init();
    esp_now_register_send_cb(OnDataSent);
    esp_now_register_recv_cb(OnDataRecv); // Call OnDataRecv to process the message when it comes in
    
    // Register peer
    memcpy(peerInfo.peer_addr, receiverAdd, 6);
    peerInfo.channel = 0;  
    peerInfo.encrypt = false;
    esp_now_add_peer(&peerInfo);

    esp_now_send(receiverAdd, (uint8_t *) &sensorCall, sizeof(sensorCall)); // action

    Serial.println( "Setup done" );
    
}


void sleepDisplay()
{
    //Now sleep the display
    pinMode(4,OUTPUT); //
    digitalWrite(4,LOW); // Should force backlight off
    tft.writecommand(ST7789_DISPOFF);// Switch off the display
    tft.writecommand(ST7789_SLPIN);// Sleep the display driver  
}

void drawData()
{
    lv_bar_set_value(ui_barUpper, upper_tank_percentage, LV_ANIM_ON);
    lv_bar_set_value(ui_barLower, lower_tank_percentage, LV_ANIM_ON);
    
    lv_label_set_text_fmt(ui_percentUpper, "%d", upper_tank_percentage);
    lv_label_set_text_fmt(ui_percentLower, "%d", lower_tank_percentage); 

    lv_label_set_text_fmt(ui_percentBattery, "%d", battery_voltage);
    lv_label_set_text_fmt(ui_valueRSSI, "%d", sensor_signal); 

    if (pump_auto_flag) {
        lv_obj_set_style_bg_color(ui_panelAuto, lv_color_hex(0x48ec58), LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_text_color(ui_labelAuto, lv_color_hex(0x00040e), LV_PART_MAIN | LV_STATE_DEFAULT);
        toggleState0 = true;
     
    } else {
        lv_obj_set_style_bg_color(ui_panelAuto, lv_color_hex(0x4899EC), LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_text_color(ui_labelAuto, lv_color_hex(0xFFFFFF), LV_PART_MAIN | LV_STATE_DEFAULT);
        toggleState0 = false;
    }

    if (pump_state) {
        lv_obj_set_style_bg_color(ui_panelPump, lv_color_hex(0x48ec58), LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_text_color(ui_labelPump, lv_color_hex(0x00040e), LV_PART_MAIN | LV_STATE_DEFAULT);
        toggleState14 = true;

    } else {
        lv_obj_set_style_bg_color(ui_panelPump, lv_color_hex(0x4899EC), LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_text_color(ui_labelPump, lv_color_hex(0xFFFFFF), LV_PART_MAIN | LV_STATE_DEFAULT);
        toggleState14 = false;
 
    }
   
}


void loop()
{
  lv_timer_handler(); /* let the GUI do its work */
  delay(5);

  // Debounce Button 0 (Toggle Switch)
  currentButtonState0 = digitalRead(inputPin0);

  if (currentButtonState0!= lastButtonState0) {
    lastDebounceTime0 = millis();
  }

  if ((millis() - lastDebounceTime0) > debounceDelay) {
    if (currentButtonState0!= buttonState0) {
      buttonState0 = currentButtonState0;
      if (buttonState0 == LOW) {
        // Toggle the state for button 0
        toggleState0 =!toggleState0; // Flip the toggle state
        if (toggleState0) {
          // Action for toggle ON
          // Example: Send a different message or perform another action
          esp_now_send(receiverAdd, (uint8_t *) &autoOn, sizeof(autoOn)); // action
          lv_obj_set_style_bg_color(ui_panelAuto, lv_color_hex(0x48ec58), LV_PART_MAIN | LV_STATE_DEFAULT);
          lv_obj_set_style_text_color(ui_labelAuto, lv_color_hex(0x00040e), LV_PART_MAIN | LV_STATE_DEFAULT);
                 
        } else {
          // Action for toggle OFF
          // Example: Send a different message or perform another action
          esp_now_send(receiverAdd, (uint8_t *) &autoOff, sizeof(autoOff)); // action
          lv_obj_set_style_bg_color(ui_panelAuto, lv_color_hex(0x4899EC), LV_PART_MAIN | LV_STATE_DEFAULT);
          lv_obj_set_style_text_color(ui_labelAuto, lv_color_hex(0xFFFFFF), LV_PART_MAIN | LV_STATE_DEFAULT);

        }
      }
    }
  }
  lastButtonState0 = currentButtonState0;

  
  // Debounce Button 14 (Toggle Switch)
  currentButtonState14 = digitalRead(inputPin14);

  if (currentButtonState14!= lastButtonState14) {
    lastDebounceTime14 = millis();
  }

  if ((millis() - lastDebounceTime14) > debounceDelay) {
    if (currentButtonState14!= buttonState14) {
      buttonState14 = currentButtonState14;
      if (buttonState14 == LOW) {
        // Toggle the state for button 14
        toggleState14 =!toggleState14; // Flip the toggle state
        if (toggleState14) {
          // Action for toggle ON
          // Example: Send a different message or perform another action
          esp_now_send(receiverAdd, (uint8_t *) &pumpOn, sizeof(pumpOn)); // Example action
          lv_obj_set_style_bg_color(ui_panelPump, lv_color_hex(0x48ec58), LV_PART_MAIN | LV_STATE_DEFAULT);
          lv_obj_set_style_text_color(ui_labelPump, lv_color_hex(0x00040e), LV_PART_MAIN | LV_STATE_DEFAULT);

          
        } else {
          // Action for toggle OFF
          // Example: Send a different message or perform another action
          esp_now_send(receiverAdd, (uint8_t *) &pumpOff, sizeof(pumpOff)); // Example action
          lv_obj_set_style_bg_color(ui_panelPump, lv_color_hex(0x4899EC), LV_PART_MAIN | LV_STATE_DEFAULT);
          lv_obj_set_style_text_color(ui_labelPump, lv_color_hex(0xFFFFFF), LV_PART_MAIN | LV_STATE_DEFAULT);          
        }
      }
    }
  }
  lastButtonState14 = currentButtonState14;

    if (millis() - startTime >= 300000) // If 5 minutes has passed or the right button pressed begin sleep
  { 
    
    //Now sleep the display
  
    sleepDisplay();
  
    // Put the ESP32 into deep sleep mode
    esp_deep_sleep_start(); // Enter deep sleep mode
  }

    
}

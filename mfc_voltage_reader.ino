#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

// Try 0x3D if screen stays blank
#define OLED_ADDRESS 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Change if you use a different GPIO
#define PIN_RAW_VOLTAGE 34
#define PIN_AMP_VOLTAGE 35

// Match your actual resistor values: (R1+R2)/R2
#define RAW_DIVIDER_RATIO 2.0

// Set to your op-amp's actual gain (e.g. 10, 50, 100)
#define AMP_GAIN 50.0

// ESP32 ADC specific constants
#define ADC_RESOLUTION 4095.0
#define V_REF 3.3

void setup() {
  Serial.begin(115200);

  if(!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }
  
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  // Send header for the python script to ignore or use
  Serial.println("Time(ms),Raw_V,Amp_Pin_V,Calc_V");
}

void loop() {
  int rawADC = analogRead(PIN_RAW_VOLTAGE);
  int ampADC = analogRead(PIN_AMP_VOLTAGE);

  float rawPinVoltage = (rawADC / ADC_RESOLUTION) * V_REF;
  float ampPinVoltage = (ampADC / ADC_RESOLUTION) * V_REF;

  float rawVoltage = rawPinVoltage * RAW_DIVIDER_RATIO;
  float calcVoltage = ampPinVoltage / AMP_GAIN;

  unsigned long currentMillis = millis();

  // Print format expected by Python script: ts, rv, av, cv
  Serial.print(currentMillis);
  Serial.print(",");
  Serial.print(rawVoltage, 4);
  Serial.print(",");
  Serial.print(ampPinVoltage, 4);
  Serial.print(",");
  Serial.println(calcVoltage, 4);

  // Update OLED
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(F("MFC Voltage Reader"));

  display.setCursor(0, 20);
  display.print(F("Raw: "));
  display.print(rawVoltage, 3);
  display.println(F(" V"));

  display.setCursor(0, 35);
  display.print(F("Amp: "));
  display.print(calcVoltage, 4);
  display.println(F(" V"));

  display.display();

  delay(200); // Wait ~200ms
}

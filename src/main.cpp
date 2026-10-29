#include <SPI.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

#include <vid.h>

// const uint32_t frames_n = 100;
// const uint64_t v[] = {0, 1, 0, 0, 0,};
const uint8_t max_y = 134;
const uint8_t max_x = 178;
uint16_t frame_cnt = 0;
uint32_t global_byte_id = 0;
uint8_t global_bit = 0;
const uint32_t max_vlq_val = (1 << 21) - 1;
uint32_t current_len = 0;
bool current_color = 0;
bool max_val = 1;
const uint16_t COLOR_ZERO = TFT_BLACK;
const uint16_t COLOR_ONE = TFT_WHITE;

uint64_t debug_data = 0;
uint64_t debug_data_2 = 0;


uint32_t readVLQSequence() {
  // Serial.println("starting vlq sequence: " + String(global_bit));
  const uint8_t vlq_bits[] = {5, 2, 1, 3, 2, 1, 1, 4, 2};
  uint32_t value = 0;
  // uint32_t bmask = 1;
  bool continuation_bit = 0;

  uint8_t cmlt_bits = 0;
  // Serial.println("Bit ini: " + String(global_bit));

  for (uint8_t vlq_id = 0; vlq_id < sizeof(vlq_bits); vlq_id++) {
    continuation_bit = (v[global_byte_id] >> (63 - global_bit)) & 1;

    if (!continuation_bit && vlq_id != 0) {
      break;
    }
    else {
      global_bit++;

      if (global_bit == 64) {
        global_bit = 0;
        global_byte_id++;
      }
    }
  

    uint8_t bits_to_read = vlq_bits[vlq_id];
    uint32_t segment_value = 0;

    for (uint8_t i = 0; i < bits_to_read; ++i) {
      // Serial.println("Bit: " + String(i) + " " + String(global_bit));
      segment_value <<= 1;

      if ((v[global_byte_id] >> (63 - global_bit)) & 1) {
          segment_value |= 1;
      }
      global_bit++;

      if (global_bit == 64) {
          global_bit = 0;
          global_byte_id++;
      }
    }
    // Serial.println("Meow 1: " + String(cmlt_bits) + " " + String(global_bit));

    value = value | (segment_value << cmlt_bits);

    cmlt_bits += bits_to_read;

    // Serial.println("Meow 2: " + String(value) +  " " + String(cmlt_bits) + " " + String(segment_value));
  }

  // Serial.println("Decoded vlq sequence: " + String(value) +  " " + String(global_bit));
  value++;
  debug_data_2 += value;
  return value;
}


void displayFrame() {
  uint8_t x = 0;
  uint8_t y = 0;

  uint16_t n = 0;
  uint16_t test_val = 0;
  uint16_t test_val_2 = 0;

  // Serial.println("Display start");

  while(y < max_y) {

    // Если длина ноль читаем новую длину
    if (current_len == 0) {
      if (max_val) {
        current_color = (v[global_byte_id] >> (63 - global_bit)) & 1;
        max_val = 0;
        global_bit++;

        if (global_bit == 64) {
          global_bit = 0;
          global_byte_id++;
        }
      }
      else {
        current_color = !current_color;
      }
      
      current_len = readVLQSequence();

      if (current_len == max_vlq_val) {
        max_val = 1;
      }
    }
    //иначе рендер
    
    // --- Optimized Drawing Logic ---
        
    // Calculate how many pixels are left on the current line
    uint8_t pixels_on_line = max_x - x;
    
    // Determine how many pixels to draw now: either the rest of the run or the rest of the line
    uint8_t pixels_to_draw = (current_len < pixels_on_line) ? current_len : pixels_on_line;
    
    // Draw the horizontal line segment
    if (pixels_to_draw > 0) {
      test_val_2 += pixels_to_draw;
      debug_data += pixels_to_draw;
      tft.drawFastHLine(x, y, pixels_to_draw, current_color ? COLOR_ONE : COLOR_ZERO);
    }

    // Update our position and the remaining length of the run
    x += pixels_to_draw;
    current_len -= pixels_to_draw;

    // If we've reached the end of a line, move to the next one
    if (x == max_x) {
        x = 0;
        y++;
        test_val += max_x;
    }

    // Serial.println("Loop pass: " + String(x) + " " + String(y) + " " + String(global_bit) + " " + String(global_byte_id) +  " " + String(current_len) +  " " + String(current_color));
  }

  // Serial.println(String(test_val_2)+" "+String(test_val) + " " + " " + String(y) + " " + String(x));
}


void setup() {
  Serial.begin(115200);
  tft.begin();
  tft.fillScreen(TFT_BLACK);
  tft.setRotation(3);

  Serial.println("Succesfully initiated");

  tft.drawFastHLine(0, 0, 238, TFT_BLUE);
  tft.drawFastHLine(0, 10, 178, TFT_GOLD);
  tft.drawFastHLine(178, 10, 60, TFT_ORANGE);
  tft.drawFastHLine(119, 67, 119, TFT_YELLOW);
  tft.drawFastHLine(119, 0, 119, TFT_PURPLE);
  tft.drawFastVLine(0, 0, 134, TFT_RED);

  Serial.println(max_vlq_val);
  Serial.println();
  delay(1000);
}


void loop() {
  // Serial.println("Current frame: " + String(frame_cnt));
  displayFrame();

  // Serial.println("Displayed frame: " + String(frame_cnt));
  // delay(1000);

  frame_cnt++;

  if (frames_n == frame_cnt) {
    frame_cnt = 0;
    global_byte_id = 0;
    global_bit = 0;
    current_len = 0;
    max_val = 1;
    current_color = 1;

    Serial.println("Display_finished");
    Serial.println(debug_data);
    Serial.println(debug_data_2);

    tft.fillScreen(TFT_BLACK);

    delay(5000);
  }

  delay(80);
}

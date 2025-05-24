#include <avr/wdt.h>
#include <EEPROM.h>

// read documenation of indicators and the watcher in https://monitait.com/docs

// Timing constants
const unsigned long TWO_MS_PULSES = 125;  // 125 pulses per 2 milliseconds
const unsigned long TEN_MS_PULSES = 625;  // 625 pulses per 10 milliseconds
const unsigned long ONE_SEC_PULSES = TEN_MS_PULSES * 100; // Number of pulses in one second
const unsigned long ONE_MIN_PULSES = ONE_SEC_PULSES * 60;   // 3,750,000 pulses per minute

// Restart interval (1 minute = 60 * 62500 = 3,750,000 pulses)
const unsigned long MIN_RESTART_INTERVAL = ONE_MIN_PULSES;

// Global timing variables
unsigned long current_time = 0;  // Current time in milliseconds
unsigned long ok_last_check_time = 0;  // Last check time for OK signal
unsigned long ng_last_check_time = 0;  // Last check time for NG signal
unsigned long last_speed_calc_time = 0;  // Last time speed was calculated
unsigned long last_speed_calc_minute_time = 0;  // Last time minute speed was calculated
unsigned long last_heartbeat_time = 0;  // Last time heartbeat LED was updated

// Debounce counters
unsigned int ok_high_count = 0;  // Counter for OK signal high state
unsigned int ng_high_count = 0;  // Counter for NG signal high state

// Serial communication
String inString = "";  // Buffer for serial input

// Input pins
const byte PIN_OK_INPUT = 2;      // OK signal input
const byte PIN_NG_INPUT = 3;      // NG signal input
const byte PIN_U_OUTPUT = 6;      // U direction output
const byte PIN_B_OUTPUT = 5;      // B direction output
const byte PIN_RPI_SIGNAL = 11;   // RPI communication signal
const byte PIN_RPI_ADDRESS = 18;  // RPI address selection
const byte PIN_WARNING_LED = 10;  // Warning LED indicator
const byte PIN_HEARTBEAT_LED = 13;// Heartbeat LED indicator
const byte PIN_RPI_RESET = 12;    // RPI reset control
const byte PIN_OK_IDENTIFIER = 8; // OK status indicator
const byte PIN_NG_IDENTIFIER = 9; // NG status indicator

// RPI communication pins
const byte PIN_RPI_DATA_IN[3] = {
  14, 15, 16
}; // RPI data input pins

const byte PIN_RPI_DATA_OUT[3] = {
  4, 7, 17
}; // RPI data output pins

long counter_ok = 0;
long counter_ng = 0;
long encoder_counter = 0;
unsigned int battery;
unsigned int analog = 0;
unsigned int counter_rpi_reboot = 1000;
unsigned int restart_counter = 1;
long counter_sum_ok_ng = 0;
unsigned long elapsed_speed = 100;
unsigned long last_pi_ping_time;
int pwmup = 255;
int pwmdown = 255;

byte output_status = 0; // Store real-time output state

byte get_byte;
byte out_pins_number;

volatile long last_encoder_count = 0;
long pulse_sec_speed = 0;

volatile long last_encoder_count_minute = 0;
long pulse_min_speed = 0;

volatile long downtime_seconds = 0;
int downtime_threshold = 10;
void(* resetFunc) (void) = 0;
#define EEPROM_PRINT_MODE 0        // 0-3: Print mode (0 for new, 1 for legacy)
#define EEPROM_VERBOSE_MODE 4      // 4-7: Verbose mode (0 for off, 1 for on)
#define EEPROM_EXT_RESET_ENABLED 8 // 8-11: External reset enabled (0 for off, 1 for on)
#define EEPROM_OK_OFFSET_DELAY 12  // 12-15: OK offset delay in pulses
#define EEPROM_OK_DEBOUNCE_PULSE 16 // 16-19: OK debounce pulse count
#define EEPROM_OK_DEBOUNCE_PERCENT 20 // 20-23: OK debounce percent
#define EEPROM_OK_ENCODER_FACTOR 24 // 24-27: OK encoder factor
#define EEPROM_NG_OFFSET_DELAY 28  // 28-31: NG offset delay in pulses
#define EEPROM_NG_DEBOUNCE_PULSE 32 // 32-35: NG debounce pulse count
#define EEPROM_NG_DEBOUNCE_PERCENT 36 // 36-39: NG debounce percent
#define EEPROM_NG_ENCODER_FACTOR 40 // 40-43: NG encoder factor
#define EEPROM_DOWNTIME_THRESHOLD 44 // 44-47: Downtime threshold
#define EEPROM_BAUD_RATE 48        // 48-51: Baud rate

// Default baud rate if EEPROM is empty
#define DEFAULT_BAUD_RATE 57600

// Convert milliseconds to pulses
#define MS_TO_PULSES(ms) (((ms) * TWO_MS_PULSES) / 2)
// Convert pulses to milliseconds
#define PULSES_TO_MS(pulses) ((pulses) * 2 / TWO_MS_PULSES)

// Default delay values in milliseconds
#define DEFAULT_OFFSET_DELAY_MS 0
#define DEFAULT_DEBOUNCE_PULSE 10
#define DEFAULT_DEBOUNCE_PERCENT 60

unsigned long ok_offset_delay = MS_TO_PULSES(DEFAULT_OFFSET_DELAY_MS);
unsigned long ok_debounce_pulse = DEFAULT_DEBOUNCE_PULSE;
unsigned long ok_debounce_percent = DEFAULT_DEBOUNCE_PERCENT;
unsigned long ng_offset_delay = MS_TO_PULSES(DEFAULT_OFFSET_DELAY_MS);
unsigned long ng_debounce_pulse = DEFAULT_DEBOUNCE_PULSE;
unsigned long ng_debounce_percent = DEFAULT_DEBOUNCE_PERCENT;
bool legacy_print_mode = false;  // false for new format, true for legacy format
bool ext_reset_enabled = false;
bool verbose_mode = false;
unsigned long baud_rate = DEFAULT_BAUD_RATE;  // Global baud rate variable

// Add these with other global variables
unsigned long counter_a_b = 0;
const unsigned int MAX_RESTART_COUNTER = 500;
const unsigned int MIN_RESTART_COUNTER = 2;
const unsigned long BASE_REBOOT_THRESHOLD = 1000;
unsigned long last_restart_time = 0;      // Track last restart time
volatile bool ok_interrupt_flag = false;
volatile bool ng_interrupt_flag = false;
volatile unsigned long ok_interrupt_time = 0;  // Changed from ok_interrupt_pulses
volatile unsigned long ng_interrupt_time = 0;  // Changed from ng_interrupt_pulses
int ok_debounce_threshold = 0;  // Pre-calculated threshold
int ng_debounce_threshold = 0;  // Pre-calculated threshold
volatile bool ok_pending_count = false;
volatile bool ng_pending_count = false;
volatile int ok_pending_encoder = 0;
volatile int ng_pending_encoder = 0;
volatile unsigned long last_speed_calc_pulses = 0;
volatile unsigned long last_speed_calc_minute_pulses = 0;
volatile unsigned long last_restart_pulses = 0;
unsigned long last_heartbeat_pulses = 0;
unsigned long heartbeat_interval_pulses = TEN_MS_PULSES * 100;  // Default to slow blink (1s)
bool heartbeat_state = false;

// Add these constants for heartbeat patterns (in pulses)
const unsigned long HEARTBEAT_SLOW = TEN_MS_PULSES * 100;    // 1 second for normal operation
const unsigned long HEARTBEAT_FAST = TEN_MS_PULSES * 20;     // 200ms for warning state
const unsigned long HEARTBEAT_DOUBLE = TEN_MS_PULSES * 10;   // 100ms for double blink
const unsigned long HEARTBEAT_SOLID = 0;      // 0 for solid on

// Add these with other global variables
unsigned long last_heartbeat_millis = 0;  // For millis-based timing

// Add these with other global variables
#define MAX_ENCODER_EVENTS 32
struct EncoderEvent {
  unsigned long scheduled_time;
  int increment;
};
EncoderEvent encoder_events[MAX_ENCODER_EVENTS];
int encoder_head = 0;
int encoder_tail = 0;
int inc = 0;  // Global increment variable

// Add these with other global variables
int ok_encoder_factor = 1;  // Default OK encoder factor
int ng_encoder_factor = 1;  // Default NG encoder factor

// Add this function to calculate thresholds
void updateDebounceThresholds() {
  ok_debounce_threshold = (ok_debounce_pulse * ok_debounce_percent) / 100;
  ng_debounce_threshold = (ng_debounce_pulse * ng_debounce_percent) / 100;
}

// Add these helper functions after the EEPROM definitions

// Write a 4-byte (32-bit) value to EEPROM
void EEPROMWriteULong(int address, unsigned long value) {
  byte byte1 = value & 0xFF;
  byte byte2 = (value >> 8) & 0xFF;
  byte byte3 = (value >> 16) & 0xFF;
  byte byte4 = (value >> 24) & 0xFF;
  EEPROM.write(address, byte1);
  EEPROM.write(address + 1, byte2);
  EEPROM.write(address + 2, byte3);
  EEPROM.write(address + 3, byte4);
}

// Read a 4-byte (32-bit) value from EEPROM
unsigned long EEPROMReadULong(int address) {
  byte byte1 = EEPROM.read(address);
  byte byte2 = EEPROM.read(address + 1);
  byte byte3 = EEPROM.read(address + 2);
  byte byte4 = EEPROM.read(address + 3);
  return ((unsigned long)byte4 << 24) | ((unsigned long)byte3 << 16) | ((unsigned long)byte2 << 8) | byte1;
}

// Initialize EEPROM with default values if empty
void initializeEEPROMIfEmpty() {
  // Check if EEPROM is empty (all bytes are 0xFF)
  bool is_empty = true;
  for (int i = 0; i < 52; i++) {  // Check first 52 bytes (all our settings)
    if (EEPROM.read(i) != 0xFF) {
      is_empty = false;
      break;
    }
  }
  
  if (is_empty) {
    // Write default values
    EEPROMWriteULong(EEPROM_PRINT_MODE, 0);
    EEPROMWriteULong(EEPROM_VERBOSE_MODE, 0);
    EEPROMWriteULong(EEPROM_EXT_RESET_ENABLED, 0);
    EEPROMWriteULong(EEPROM_OK_OFFSET_DELAY, DEFAULT_OFFSET_DELAY_MS);
    EEPROMWriteULong(EEPROM_OK_DEBOUNCE_PULSE, DEFAULT_DEBOUNCE_PULSE);
    EEPROMWriteULong(EEPROM_OK_DEBOUNCE_PERCENT, DEFAULT_DEBOUNCE_PERCENT);
    EEPROMWriteULong(EEPROM_NG_OFFSET_DELAY, DEFAULT_OFFSET_DELAY_MS);
    EEPROMWriteULong(EEPROM_NG_DEBOUNCE_PULSE, DEFAULT_DEBOUNCE_PULSE);
    EEPROMWriteULong(EEPROM_NG_DEBOUNCE_PERCENT, DEFAULT_DEBOUNCE_PERCENT);
    EEPROMWriteULong(EEPROM_DOWNTIME_THRESHOLD, 10);
    EEPROMWriteULong(EEPROM_BAUD_RATE, DEFAULT_BAUD_RATE);
    EEPROMWriteULong(EEPROM_OK_ENCODER_FACTOR, 1);  // Default OK encoder factor
    EEPROMWriteULong(EEPROM_NG_ENCODER_FACTOR, 1);  // Default NG encoder factor
  }
}

void setup() {
  wdt_enable(WDTO_8S);  // 8 second timeout
  
  // Initialize EEPROM with default values if empty
  initializeEEPROMIfEmpty();
  
  // Read baud rate from EEPROM
  baud_rate = EEPROMReadULong(EEPROM_BAUD_RATE);
  if (baud_rate == 0 || baud_rate == 0xFFFFFFFF) {  // If EEPROM is empty or invalid
    baud_rate = DEFAULT_BAUD_RATE;
    EEPROMWriteULong(EEPROM_BAUD_RATE, baud_rate);
  }
  
  // Initialize serial with the correct baud rate
  switch(baud_rate) {
    case 9600:
      Serial.begin(9600);
      break;
    case 19200:
      Serial.begin(19200);
      break;
    case 38400:
      Serial.begin(38400);
      break;
    case 57600:
      Serial.begin(57600);
      break;
    case 115200:
      Serial.begin(115200);
      break;
    default:
      Serial.begin(DEFAULT_BAUD_RATE);  // Fallback to default
      break;
  }
  
  Serial.setTimeout(100); // Add timeout for serial operations
  for(int i = 0; i < 3; i++){
    pinMode(PIN_RPI_DATA_IN[i], INPUT_PULLUP);
    pinMode(PIN_RPI_DATA_OUT[i], OUTPUT);
  }
  
  pinMode(PIN_OK_INPUT, INPUT);
  pinMode(PIN_NG_INPUT, INPUT);
  pinMode(PIN_RPI_ADDRESS, INPUT_PULLUP);
  pinMode(PIN_RPI_SIGNAL, INPUT_PULLUP);

  pinMode(PIN_OK_IDENTIFIER, OUTPUT);
  pinMode(PIN_NG_IDENTIFIER, OUTPUT);
  pinMode(PIN_RPI_RESET, OUTPUT);
  pinMode(PIN_HEARTBEAT_LED, OUTPUT);
  pinMode(PIN_WARNING_LED, OUTPUT);
  digitalWrite(PIN_WARNING_LED, HIGH);
  
  attachInterrupt(digitalPinToInterrupt(PIN_OK_INPUT), count_up_ok, RISING);
  attachInterrupt(digitalPinToInterrupt(PIN_NG_INPUT), count_up_ng, RISING);

  TCCR0B = TCCR0B & B11111000 | B00000001; // for PWM frequency of 62500.00 Hz/ B and U outputs

  // Read settings from EEPROM and convert to pulses
  unsigned long ok_od = EEPROMReadULong(EEPROM_OK_OFFSET_DELAY);
  unsigned long ok_dp = EEPROMReadULong(EEPROM_OK_DEBOUNCE_PULSE);
  unsigned long ok_dl = EEPROMReadULong(EEPROM_OK_DEBOUNCE_PERCENT);
  unsigned long ng_od = EEPROMReadULong(EEPROM_NG_OFFSET_DELAY);
  unsigned long ng_dp = EEPROMReadULong(EEPROM_NG_DEBOUNCE_PULSE);
  unsigned long ng_dl = EEPROMReadULong(EEPROM_NG_DEBOUNCE_PERCENT);
  
  // Validate and set default values if EEPROM values are invalid
  ok_offset_delay = (ok_od == 0 || ok_od == 0xFFFFFFFF) ? MS_TO_PULSES(DEFAULT_OFFSET_DELAY_MS) : MS_TO_PULSES(ok_od);
  ok_debounce_pulse = (ok_dp == 0 || ok_dp == 0xFFFFFFFF) ? DEFAULT_DEBOUNCE_PULSE : ok_dp;
  ok_debounce_percent = (ok_dl == 0 || ok_dl == 0xFFFFFFFF) ? DEFAULT_DEBOUNCE_PERCENT : ok_dl;
  ng_offset_delay = (ng_od == 0 || ng_od == 0xFFFFFFFF) ? MS_TO_PULSES(DEFAULT_OFFSET_DELAY_MS) : MS_TO_PULSES(ng_od);
  ng_debounce_pulse = (ng_dp == 0 || ng_dp == 0xFFFFFFFF) ? DEFAULT_DEBOUNCE_PULSE : ng_dp;
  ng_debounce_percent = (ng_dl == 0 || ng_dl == 0xFFFFFFFF) ? DEFAULT_DEBOUNCE_PERCENT : ng_dl;
  
  // Read mode settings from EEPROM
  unsigned long stored_legacy = EEPROMReadULong(EEPROM_PRINT_MODE);
  unsigned long stored_verbose = EEPROMReadULong(EEPROM_VERBOSE_MODE);
  unsigned long stored_ext_reset = EEPROMReadULong(EEPROM_EXT_RESET_ENABLED);
  
  // Set defaults if EEPROM is empty
  if (stored_legacy == 0 || stored_legacy == 0xFFFFFFFF) {
    legacy_print_mode = false;  // Default to off (new format)
    EEPROMWriteULong(EEPROM_PRINT_MODE, 0);
  } else {
    legacy_print_mode = (stored_legacy == 1);
  }
  
  if (stored_verbose == 0 || stored_verbose == 0xFFFFFFFF) {
    verbose_mode = false;  // Default to off
    EEPROMWriteULong(EEPROM_VERBOSE_MODE, 0);
  } else {
    verbose_mode = (stored_verbose == 1);
  }
  
  if (stored_ext_reset == 0 || stored_ext_reset == 0xFFFFFFFF) {
    ext_reset_enabled = false;  // Default to disabled
    EEPROMWriteULong(EEPROM_EXT_RESET_ENABLED, 0);
  } else {
    ext_reset_enabled = (stored_ext_reset == 1);
  }
  
  downtime_threshold = EEPROMReadULong(EEPROM_DOWNTIME_THRESHOLD);
  if (downtime_threshold == 0) {  // If EEPROM is empty (0), set default value
    downtime_threshold = 10;
    EEPROMWriteULong(EEPROM_DOWNTIME_THRESHOLD, downtime_threshold);
  }

  // Read encoder factors from EEPROM
  ok_encoder_factor = EEPROMReadULong(EEPROM_OK_ENCODER_FACTOR);
  if (ok_encoder_factor == 0xFFFFFFFF) {  // Only set default if EEPROM is empty
    ok_encoder_factor = 1;
    EEPROMWriteULong(EEPROM_OK_ENCODER_FACTOR, ok_encoder_factor);
  }
  
  ng_encoder_factor = EEPROMReadULong(EEPROM_NG_ENCODER_FACTOR);
  if (ng_encoder_factor == 0xFFFFFFFF) {  // Only set default if EEPROM is empty
    ng_encoder_factor = 1;
    EEPROMWriteULong(EEPROM_NG_ENCODER_FACTOR, ng_encoder_factor);
  }

  // Calculate initial thresholds
  updateDebounceThresholds();
}

void loop() {
  // Reset watchdog at the start of each loop
  wdt_reset();
  
  // Get current time once for this loop iteration
  current_time = millis();
  
  handleSerialAndAnalogData();
  
  // Add timeout protection for RPI communication
  if (digitalRead(PIN_RPI_SIGNAL)==LOW){
    last_pi_ping_time = current_time;
    heartbeat_state = !heartbeat_state;
    restart_counter = 1;
    counter_sum_ok_ng = 0;
    get_byte = 0;
    for(int i = 0; i < 3; i++){
      if(digitalRead(PIN_RPI_DATA_IN[i]) == 1)
        bitSet(get_byte, i);
      else
        bitClear(get_byte, i);
    }
    bitClear(get_byte, 3); bitClear(get_byte, 4); bitClear(get_byte, 5); bitClear(get_byte, 6); bitClear(get_byte, 7);
    if(digitalRead(PIN_RPI_ADDRESS)==LOW){
      counter_ng = counter_ng - get_byte;
    }
    else{
      counter_ok = counter_ok - get_byte;
    }
    while (digitalRead(PIN_RPI_SIGNAL)==LOW){
      digitalWrite(PIN_OK_IDENTIFIER, LOW);
      digitalWrite(PIN_NG_IDENTIFIER, LOW);
      handleSerialAndAnalogData();
    }
  }
  else {
    if (counter_ok > 0){
      digitalWrite(PIN_OK_IDENTIFIER, HIGH);
      digitalWrite(PIN_NG_IDENTIFIER, LOW);
      if (counter_ok < 8)
        out_pins_number = counter_ok % 8;
      else if (counter_ok >= 7)
        out_pins_number = 7;
      put_byte_on_pins(out_pins_number);
      delay(5);  
    }

    else if (counter_ng > 0){
      digitalWrite(PIN_OK_IDENTIFIER, LOW);
      digitalWrite(PIN_NG_IDENTIFIER, HIGH);
      if (counter_ng < 16)
        out_pins_number = counter_ng % 8;
      else if (counter_ng >= 7)
        out_pins_number = 7;
      put_byte_on_pins(out_pins_number);
      delay(5);   
    }

    else if (counter_ok + counter_ng <= 0){
      if (battery < 780){
        out_pins_number = int(battery/132) ;
        digitalWrite(PIN_OK_IDENTIFIER, HIGH);
        digitalWrite(PIN_NG_IDENTIFIER, HIGH);
        put_byte_on_pins(out_pins_number);
      }
      else{
        out_pins_number = int(analog/132) ;
        digitalWrite(PIN_OK_IDENTIFIER, LOW);
        digitalWrite(PIN_NG_IDENTIFIER, LOW);
        put_byte_on_pins(out_pins_number);
      }
      delay(5); 
    }

  }  
  
  // Update heartbeat LED with new pattern
  updateHeartbeatLED();
}

void put_byte_on_pins(byte in_byte){
  for(int i = 0; i < 3; i++){
    digitalWrite(PIN_RPI_DATA_OUT[i], bitRead(in_byte, i));
  }
  return;
}

void count_up_ok() {
  if (ok_debounce_pulse == 0) {  // If no debounce delay
    // Handle short debounce directly in interrupt
    if (digitalRead(PIN_OK_INPUT) == HIGH) {
      inc = (digitalRead(PIN_NG_INPUT) == HIGH) ? -1 : 1;
      encoder_events[encoder_head] = {current_time + ok_offset_delay, inc * ok_encoder_factor};
      encoder_head = (encoder_head + 1) % MAX_ENCODER_EVENTS;
      counter_ok++;
    }
  } else {
    // For longer debounces, set flag for main loop
    ok_interrupt_flag = true;
    ok_interrupt_time = millis();
  }
}

void count_up_ng() {
  if (ng_debounce_pulse == 0) {  // If no debounce delay
    // Handle short debounce directly in interrupt
    if (digitalRead(PIN_NG_INPUT) == HIGH) {
      inc = (digitalRead(PIN_OK_INPUT) == HIGH) ? 1 : -1;
      encoder_events[encoder_head] = {current_time + ng_offset_delay, inc * ng_encoder_factor};
      encoder_head = (encoder_head + 1) % MAX_ENCODER_EVENTS;
      counter_ng++;
    }
  } else {
    // For longer debounces, set flag for main loop
    ng_interrupt_flag = true;
    ng_interrupt_time = millis();
  }
}

void process_encoder_events() {
  while (encoder_tail != encoder_head && encoder_events[encoder_tail].scheduled_time <= current_time) {
    encoder_counter += encoder_events[encoder_tail].increment;
    encoder_tail = (encoder_tail + 1) % MAX_ENCODER_EVENTS;
  }
}

void handleSerialAndAnalogData() {
  // Get analog data
  battery = analogRead(A6);  
  analog = analogRead(A7);

  // Handle OK signal debouncing
  if (ok_interrupt_flag) {
    if (current_time - ok_last_check_time >= 1) {  // Check every pulse
      ok_last_check_time = current_time;
      
      if (digitalRead(PIN_OK_INPUT) == HIGH) {
        ok_high_count += 1;  // Increment by 1 pulse
      }
      
      if (ok_high_count >= ok_debounce_pulse) {
        if (ok_high_count > ok_debounce_threshold) {
          inc = (digitalRead(PIN_NG_INPUT) == HIGH) ? -1 : 1;
          encoder_events[encoder_head] = {current_time + ok_offset_delay, inc * ok_encoder_factor};
          encoder_head = (encoder_head + 1) % MAX_ENCODER_EVENTS;
          counter_ok++;
        }
        
        ok_high_count = 0;
        ok_interrupt_flag = false;
      }
    }
  }

  // Handle NG signal debouncing
  if (ng_interrupt_flag) {
    if (current_time - ng_last_check_time >= 1) {  // Check every pulse
      ng_last_check_time = current_time;
      
      if (digitalRead(PIN_NG_INPUT) == HIGH) {
        ng_high_count += 1;  // Increment by 1 pulse
      }
      
      if (ng_high_count >= ng_debounce_pulse) {
        if (ng_high_count > ng_debounce_threshold) {
          inc = (digitalRead(PIN_OK_INPUT) == HIGH) ? 1 : -1;
          encoder_events[encoder_head] = {current_time + ng_offset_delay, inc * ng_encoder_factor};
          encoder_head = (encoder_head + 1) % MAX_ENCODER_EVENTS;
          counter_ng++;
        }
        
        ng_high_count = 0;
        ng_interrupt_flag = false;
      }
    }
  }

  // Process any pending encoder events
  process_encoder_events();

  // Handle serial data
  while (Serial.available() > 0) {
    inString = Serial.readStringUntil('\n');
    if (inString.length() == 0) continue;

    char cmd = inString[0];
    switch (cmd) {
      case 'o':
      case 'n': {
        // Handle OK/NG configuration commands
        int firstComma = inString.indexOf(',');
        int secondComma = inString.indexOf(',', firstComma + 1);
        
        if (firstComma != -1 && secondComma != -1) {
          String subCmd = inString.substring(firstComma + 1, secondComma);
          int value = inString.substring(secondComma + 1).toInt();
          
          if (cmd == 'o') {
            if (subCmd == "od") {
              if (value >= 0) {
                ok_offset_delay = MS_TO_PULSES(value);
                EEPROMWriteULong(EEPROM_OK_OFFSET_DELAY, value);
              }
            } else if (subCmd == "dp") {
              if (value >= 0) {
                ok_debounce_pulse = value;
                EEPROMWriteULong(EEPROM_OK_DEBOUNCE_PULSE, value);
                updateDebounceThresholds();
              }
            } else if (subCmd == "dl") {
              if (value >= 0 && value <= 100) {
                ok_debounce_percent = value;
                EEPROMWriteULong(EEPROM_OK_DEBOUNCE_PERCENT, ok_debounce_percent);
                updateDebounceThresholds();
              }
            } else if (subCmd == "ef") {
              if (value == (int)value) {  // Ensure it's an integer
                ok_encoder_factor = (int)value;
                EEPROMWriteULong(EEPROM_OK_ENCODER_FACTOR, ok_encoder_factor);
              }
            }
          } else { // cmd == 'n'
            if (subCmd == "od") {
              if (value >= 0) {
                ng_offset_delay = MS_TO_PULSES(value);
                EEPROMWriteULong(EEPROM_NG_OFFSET_DELAY, value);
              }
            } else if (subCmd == "dp") {
              if (value >= 0) {
                ng_debounce_pulse = value;
                EEPROMWriteULong(EEPROM_NG_DEBOUNCE_PULSE, value);
                updateDebounceThresholds();
              }
            } else if (subCmd == "dl") {
              if (value >= 0 && value <= 100) {
                ng_debounce_percent = value;
                EEPROMWriteULong(EEPROM_NG_DEBOUNCE_PERCENT, ng_debounce_percent);
                updateDebounceThresholds();
              }
            } else if (subCmd == "ef") {
              if (value == (int)value) {  // Ensure it's an integer
                ng_encoder_factor = (int)value;
                EEPROMWriteULong(EEPROM_NG_ENCODER_FACTOR, ng_encoder_factor);
              }
            }
          }
        }
        break;
      }

      case '1':
        analogWrite(PIN_U_OUTPUT, 255 - pwmup);
        analogWrite(PIN_B_OUTPUT, 255);
        updateOutputStatus(1, 0, -1);
        break;

      case '2':
        analogWrite(PIN_U_OUTPUT, 255);
        analogWrite(PIN_B_OUTPUT, 255 - pwmdown);
        updateOutputStatus(0, 1, -1);
        break;

      case '3':
        encoder_counter = 0;
        break;

      case '4': {
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          int temp_pwm = inString.substring(commandIndex + 1).toInt();
          pwmup = (temp_pwm >= 0 && temp_pwm <= 255) ? temp_pwm : 255;
        }
        break;
      }

      case '5': {
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          int temp_pwm = inString.substring(commandIndex + 1).toInt();
          pwmdown = (temp_pwm >= 0 && temp_pwm <= 255) ? temp_pwm : 255;
        }
        break;
      }

      case '6':
        digitalWrite(PIN_WARNING_LED, LOW);
        updateOutputStatus(-1, -1, 0);
        break;

      case '7':
        digitalWrite(PIN_WARNING_LED, HIGH);
        updateOutputStatus(-1, -1, 1);
        break;

      case '8':
        analogWrite(PIN_U_OUTPUT, 255);
        analogWrite(PIN_B_OUTPUT, 255);
        updateOutputStatus(0, 0, -1);
        break;

      case '9':
        analogWrite(PIN_U_OUTPUT, 255 - pwmup);
        analogWrite(PIN_B_OUTPUT, 255 - pwmdown);
        updateOutputStatus(1, 1, -1);
        break;

      case 'a': {
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          counter_ok = counter_ok - inString.substring(commandIndex + 1).toInt();
        }
        break;
      }

      case 'b': {
        // Handle NG counter adjustment
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          counter_ng = counter_ng - inString.substring(commandIndex + 1).toInt();
        }
        break;
      }

      case 'd': {
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          int temp_threshold = inString.substring(commandIndex + 1).toInt();
          if (temp_threshold > 0) {
            downtime_threshold = temp_threshold;
            EEPROMWriteULong(EEPROM_DOWNTIME_THRESHOLD, downtime_threshold);
          }
        }
        break;
      }

      case 's': {
        // Handle baud rate setting
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          unsigned long new_baud = inString.substring(commandIndex + 1).toInt();
          // Only allow standard baud rates
          if (new_baud == 9600 || new_baud == 19200 || new_baud == 38400 || 
              new_baud == 57600 || new_baud == 115200) {
            // Save the new baud rate
            EEPROMWriteULong(EEPROM_BAUD_RATE, new_baud);
            
            // Change baud rate immediately
            Serial.end();
            delay(100);
            Serial.begin(new_baud);
            
          }
        }
        break;
      }

      case 'e': {
        // Handle external reset relay control
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          int value = inString.substring(commandIndex + 1).toInt();
          ext_reset_enabled = (value == 1);
          EEPROMWriteULong(EEPROM_EXT_RESET_ENABLED, ext_reset_enabled ? 1 : 0);
        }
        break;
      }

      case 'v': {
        // Handle verbose mode setting
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          int value = inString.substring(commandIndex + 1).toInt();
          verbose_mode = (value == 1);
        }
        break;
      }

      case 'l': {
        // Handle legacy print mode setting
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          int value = inString.substring(commandIndex + 1).toInt();
          legacy_print_mode = (value == 1);
          EEPROMWriteULong(EEPROM_PRINT_MODE, legacy_print_mode ? 1 : 0);
        }
        break;
      }

      default:
        break;
    }
  }

  printInfo();
  
  // Update pulse per second speed
  if (current_time - last_speed_calc_time >= ONE_SEC_PULSES) { 
    pulse_sec_speed = (encoder_counter - last_encoder_count); // Pulses per second (PPS)
    last_encoder_count = encoder_counter;
    last_speed_calc_time = current_time;
  }

  // Update pulse per minute speed
  if (current_time - last_speed_calc_minute_time >= ONE_SEC_PULSES * downtime_threshold) { 
    pulse_min_speed = (encoder_counter - last_encoder_count_minute) * (downtime_threshold > 0 ? (60 / downtime_threshold) : 1); // Pulses per minute
    last_encoder_count_minute = encoder_counter;
    last_speed_calc_minute_time = current_time;
    if (pulse_min_speed == 0) {
      downtime_seconds += downtime_threshold;
    }
  }

  // Handle RPI reset functionality only if external reset is enabled
  if (ext_reset_enabled) {
    counter_a_b = counter_ok + counter_ng;

    if (counter_a_b > counter_rpi_reboot) {
      // Check if enough time has passed since last restart
      if (current_time - last_restart_time >= MIN_RESTART_INTERVAL) {
        // Reset RPI
        digitalWrite(PIN_RPI_RESET, HIGH);
        delay(1000);
        digitalWrite(PIN_RPI_RESET, LOW);
        
        if (restart_counter < MAX_RESTART_COUNTER) {
          restart_counter = min(restart_counter * 2, MAX_RESTART_COUNTER);
          counter_rpi_reboot = (pulse_sec_speed + BASE_REBOOT_THRESHOLD) * restart_counter;
        } else {
          restart_counter = MAX_RESTART_COUNTER - 1;
          resetFunc();
        }
        delay(1000);
        
        last_restart_time = current_time;
      }
    }

    if ((counter_a_b < counter_rpi_reboot/100) && (restart_counter > MIN_RESTART_COUNTER)) {
      restart_counter = max(restart_counter/2, MIN_RESTART_COUNTER);
      counter_rpi_reboot = (pulse_sec_speed + BASE_REBOOT_THRESHOLD) * restart_counter;
    }
  }
}

void updateOutputStatus(int up, int down, int warn) {
  if (up == 1) bitSet(output_status, 0); // UP ON
  if (up == 0) bitClear(output_status, 0); // UP OFF
  
  if (down == 1) bitSet(output_status, 1); // DOWN ON
  if (down == 0) bitClear(output_status, 1); // DOWN OFF
  
  if (warn == 1) bitSet(output_status, 2); // WARNING ON
  if (warn == 0) bitClear(output_status, 2); // WARNING OFF
}

void printInfo() {
  if (!legacy_print_mode) {
    // Essential data (always printed)
    Serial.print("ENC:"); Serial.print(encoder_counter); Serial.print(",");
    Serial.print("OKC:"); Serial.print(counter_ok); Serial.print(",");
    Serial.print("NGC:"); Serial.print(counter_ng); Serial.print(",");
    Serial.print("PPS:"); Serial.print(pulse_sec_speed); Serial.print(",");
    Serial.print("PPM:"); Serial.print(pulse_min_speed); Serial.print(",");
    Serial.print("DWS:"); Serial.print(downtime_seconds); Serial.print(",");
    Serial.print("ANG:"); Serial.print(analog); Serial.print(",");
    Serial.print("PWR:"); Serial.print(battery); Serial.print(",");
    Serial.print("STS:"); Serial.print(output_status);

    // Verbose data (only printed if verbose_mode is true)
    if (verbose_mode) {
      Serial.print(",");
      Serial.print("OOD:"); Serial.print(PULSES_TO_MS(ok_offset_delay)); Serial.print(",");
      Serial.print("ODP:"); Serial.print(ok_debounce_pulse); Serial.print(",");
      Serial.print("ODL:"); Serial.print(ok_debounce_percent); Serial.print(",");
      Serial.print("OEF:"); Serial.print(ok_encoder_factor); Serial.print(",");  // Add OK encoder factor
      Serial.print("NOD:"); Serial.print(PULSES_TO_MS(ng_offset_delay)); Serial.print(",");
      Serial.print("NDP:"); Serial.print(ng_debounce_pulse); Serial.print(",");
      Serial.print("NDL:"); Serial.print(ng_debounce_percent); Serial.print(",");
      Serial.print("NEF:"); Serial.print(ng_encoder_factor); Serial.print(",");  // Add NG encoder factor
      Serial.print("EXT:"); Serial.print(ext_reset_enabled ? "1" : "0"); Serial.print(",");
      Serial.print("BUD:"); Serial.print(baud_rate); Serial.print(",");
      Serial.print("DWT:"); Serial.print(downtime_threshold);
    }
    Serial.print("\n");
  } else {
    // legacy print mode
    Serial.print("Encoder:"); Serial.print(encoder_counter); Serial.print(",");
    Serial.print("Red:0,");
    Serial.print("Green:0,");
    Serial.print("Blue:0,");
    Serial.print("Color:0,");
    Serial.print("\n");
  }
  wdt_reset();
}

// Add this function to handle heartbeat patterns
void updateHeartbeatLED() {
  // Check for error conditions first
  if (battery < 780) {  // Low battery warning
    if (current_time - last_heartbeat_time >= TWO_MS_PULSES*100) {  // 200ms fast blink
      last_heartbeat_time = current_time;
      heartbeat_state = !heartbeat_state;
      digitalWrite(PIN_HEARTBEAT_LED, heartbeat_state);
    }
  } else if (counter_sum_ok_ng > counter_rpi_reboot / 2) {  // High error rate
    if (current_time - last_heartbeat_time >= TWO_MS_PULSES*200) {  // 400ms fast blink
      last_heartbeat_time = current_time;
      heartbeat_state = !heartbeat_state;
      digitalWrite(PIN_HEARTBEAT_LED, heartbeat_state);
    }
  } else if (digitalRead(PIN_RPI_SIGNAL) == HIGH && (current_time - last_pi_ping_time > ONE_MIN_PULSES * 5)) {  // RPI communication error
    // Double blink pattern
    if (current_time - last_heartbeat_time >= TWO_MS_PULSES*150) {  // 300ms cycle
      last_heartbeat_time = current_time;
      heartbeat_state = true;
    } else if (current_time - last_heartbeat_time >= TWO_MS_PULSES*100) {  // 200ms
      heartbeat_state = false;
    } else if (current_time - last_heartbeat_time >= TWO_MS_PULSES*50) {  // 100ms
      heartbeat_state = true;
    } else {
      heartbeat_state = false;
    }
    digitalWrite(PIN_HEARTBEAT_LED, heartbeat_state);
  } else {
    // Normal operation - 1 second blink
    if (current_time - last_heartbeat_time >= ONE_SEC_PULSES) {  // 1 second
      last_heartbeat_time = current_time;
      heartbeat_state = !heartbeat_state;
      digitalWrite(PIN_HEARTBEAT_LED, heartbeat_state);
    }
  }
}


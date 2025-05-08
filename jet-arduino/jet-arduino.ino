#include <avr/wdt.h>
#include <EEPROM.h>

// read documenation of indicators and the watcher in https://monitait.com/docs

// Timing constants
const unsigned long TEN_MS_PULSES = 625;  // 625 pulses per 10 milliseconds
const unsigned long ONE_SEC_PULSES = TEN_MS_PULSES * 100; // Number of pulses in one second
const unsigned long ONE_MIN_PULSES = ONE_SEC_PULSES * 60;   // 3,750,000 pulses per minute

// Restart interval (1 minute = 60 * 62500 = 3,750,000 pulses)
const unsigned long MIN_RESTART_INTERVAL = ONE_MIN_PULSES;

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
unsigned long last_speed_calc_time = 0;

volatile long last_encoder_count_minute = 0;
long pulse_min_speed = 0;
unsigned long last_speed_calc_time_minute = 0;

volatile long downtime_seconds = 0;
int downtime_threshold = 10;
void(* resetFunc) (void) = 0;

#define EEPROM_OK_OFFSET_DELAY 0
#define EEPROM_OK_DEBOUNCE_DELAY 1
#define EEPROM_OK_DEBOUNCE_PERCENT 2
#define EEPROM_NG_OFFSET_DELAY 3
#define EEPROM_NG_DEBOUNCE_DELAY 4
#define EEPROM_NG_DEBOUNCE_PERCENT 5
#define EEPROM_PRINT_MODE 6
#define EEPROM_EXT_RESET_ENABLED 7
#define EEPROM_DOWNTIME_THRESHOLD 8
#define EEPROM_BAUD_RATE 9
#define EEPROM_VERBOSE_MODE 10

// Default baud rate if EEPROM is empty
#define DEFAULT_BAUD_RATE 57600

// Convert milliseconds to pulses
#define MS_TO_PULSES(ms) ((ms) * TEN_MS_PULSES / 10)
// Convert pulses to milliseconds
#define PULSES_TO_MS(pulses) ((pulses) * 10 / TEN_MS_PULSES)

// Default delay values in milliseconds
#define DEFAULT_OFFSET_DELAY_MS 0
#define DEFAULT_DEBOUNCE_DELAY_MS 10
#define DEFAULT_DEBOUNCE_PERCENT 60

int ok_offset_delay = MS_TO_PULSES(DEFAULT_OFFSET_DELAY_MS);
int ok_debounce_delay = MS_TO_PULSES(DEFAULT_DEBOUNCE_DELAY_MS);
int ok_debounce_percent = DEFAULT_DEBOUNCE_PERCENT;
int ng_offset_delay = MS_TO_PULSES(DEFAULT_OFFSET_DELAY_MS);
int ng_debounce_delay = MS_TO_PULSES(DEFAULT_DEBOUNCE_DELAY_MS);
int ng_debounce_percent = DEFAULT_DEBOUNCE_PERCENT;
char print_mode = 'n'; // 'l' for legacy, 'n' for new
bool ext_reset_enabled = false;
bool verbose_mode = false;

// Add these with other global variables
unsigned long counter_a_b = 0;
const unsigned int MAX_RESTART_COUNTER = 500;
const unsigned int MIN_RESTART_COUNTER = 2;
const unsigned long BASE_REBOOT_THRESHOLD = 1000;
unsigned long last_restart_time = 0;      // Track last restart time
volatile bool ok_interrupt_flag = false;
volatile bool ng_interrupt_flag = false;
volatile unsigned long ok_interrupt_pulses = 0;
volatile unsigned long ng_interrupt_pulses = 0;
int ok_debounce_threshold = 0;  // Pre-calculated threshold
int ng_debounce_threshold = 0;  // Pre-calculated threshold
volatile bool ok_pending_count = false;
volatile bool ng_pending_count = false;
volatile int ok_pending_encoder = 0;
volatile int ng_pending_encoder = 0;
volatile unsigned long last_speed_calc_pulses = 0;
volatile unsigned long last_speed_calc_minute_pulses = 0;
volatile unsigned long last_restart_pulses = 0;
volatile unsigned long last_pi_ping_pulses = 0;

// Add this function to calculate thresholds
void updateDebounceThresholds() {
  ok_debounce_threshold = (ok_debounce_delay * ok_debounce_percent) / 100;
  ng_debounce_threshold = (ng_debounce_delay * ng_debounce_percent) / 100;
}

void setup() {
  wdt_enable(WDTO_8S);  // 8 second timeout
  
  // Read baud rate from EEPROM
  unsigned long baud_rate = EEPROM.read(EEPROM_BAUD_RATE);
  if (baud_rate == 0) {  // If EEPROM is empty (0), set default value
    baud_rate = DEFAULT_BAUD_RATE;
    EEPROM.write(EEPROM_BAUD_RATE, baud_rate);
  }
  Serial.begin(baud_rate);
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
  ok_offset_delay = MS_TO_PULSES(EEPROM.read(EEPROM_OK_OFFSET_DELAY));
  ok_debounce_delay = MS_TO_PULSES(EEPROM.read(EEPROM_OK_DEBOUNCE_DELAY));
  ok_debounce_percent = EEPROM.read(EEPROM_OK_DEBOUNCE_PERCENT);
  ng_offset_delay = MS_TO_PULSES(EEPROM.read(EEPROM_NG_OFFSET_DELAY));
  ng_debounce_delay = MS_TO_PULSES(EEPROM.read(EEPROM_NG_DEBOUNCE_DELAY));
  ng_debounce_percent = EEPROM.read(EEPROM_NG_DEBOUNCE_PERCENT);
  print_mode = EEPROM.read(EEPROM_PRINT_MODE);
  ext_reset_enabled = EEPROM.read(EEPROM_EXT_RESET_ENABLED);
  downtime_threshold = EEPROM.read(EEPROM_DOWNTIME_THRESHOLD);
  verbose_mode = EEPROM.read(EEPROM_VERBOSE_MODE);
  if (downtime_threshold == 0) {  // If EEPROM is empty (0), set default value
    downtime_threshold = 10;
    EEPROM.write(EEPROM_DOWNTIME_THRESHOLD, downtime_threshold);
  }

  // Calculate initial thresholds
  updateDebounceThresholds();
}

void loop() {
  // Reset watchdog at the start of each loop
  wdt_reset();
  
  handleSerialAndAnalogData();
  
  // Add timeout protection for RPI communication
  if (digitalRead(PIN_RPI_SIGNAL)==LOW){
    last_pi_ping_time = millis();
    restart_counter = 1;
    counter_sum_ok_ng = 0;
    digitalWrite(PIN_HEARTBEAT_LED, !digitalRead(PIN_HEARTBEAT_LED));
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
  
}

void put_byte_on_pins(byte in_byte){
  for(int i = 0; i < 3; i++){
    digitalWrite(PIN_RPI_DATA_OUT[i], bitRead(in_byte, i));
  }
  return;
}

void count_up_ok() {
  ok_interrupt_flag = true;
  ok_interrupt_pulses = encoder_counter;
}

void count_up_ng() {
  ng_interrupt_flag = true;
  ng_interrupt_pulses = encoder_counter;
}

void handleSerialAndAnalogData() {
  // Get current pulses count
  unsigned long current_pulses = encoder_counter;
  
  // Get analog data
  battery = analogRead(A6);  
  analog = analogRead(A7);

  // Handle OK signal debouncing
  if (ok_interrupt_flag) {
    static int ok_high_count = 0;
    static unsigned long ok_last_check_pulses = 0;
    
    if (current_pulses - ok_last_check_pulses >= TEN_MS_PULSES / 10) {  // 1ms equivalent
      ok_last_check_pulses = current_pulses;
      
      if (digitalRead(PIN_OK_INPUT) == HIGH) {
        ok_high_count++;
      }
      
      if (ok_high_count >= ok_debounce_delay) {
        if (ok_high_count > ok_debounce_threshold) {
          ok_pending_count = true;
          ok_pending_encoder = (digitalRead(PIN_NG_INPUT) == HIGH) ? -1 : 1;
          ok_interrupt_pulses = current_pulses;
        }
        
        ok_high_count = 0;
        ok_interrupt_flag = false;
      }
    }
  }

  // Handle NG signal debouncing
  if (ng_interrupt_flag) {
    static int ng_high_count = 0;
    static unsigned long ng_last_check_pulses = 0;
    
    if (current_pulses - ng_last_check_pulses >= TEN_MS_PULSES / 10) {  // 1ms equivalent
      ng_last_check_pulses = current_pulses;
      
      if (digitalRead(PIN_NG_INPUT) == HIGH) {
        ng_high_count++;
      }
      
      if (ng_high_count >= ng_debounce_delay) {
        if (ng_high_count > ng_debounce_threshold) {
          ng_pending_count = true;
          ng_pending_encoder = (digitalRead(PIN_OK_INPUT) == HIGH) ? 1 : -1;
          ng_interrupt_pulses = current_pulses;
        }
        
        ng_high_count = 0;
        ng_interrupt_flag = false;
      }
    }
  }

  // Handle pending counts after offset delay
  // Check OK pending count
  if (ok_pending_count && (current_pulses - ok_interrupt_pulses >= ok_offset_delay)) {
    counter_ok++;
    encoder_counter += ok_pending_encoder;
    ok_pending_count = false;
  }

  // Check NG pending count
  if (ng_pending_count && (current_pulses - ng_interrupt_pulses >= ng_offset_delay)) {
    counter_ng++;
    encoder_counter += ng_pending_encoder;
    ng_pending_count = false;
  }

  // Handle serial data
  while (Serial.available() > 0) {
    String inString = Serial.readStringUntil('\n');
    if (inString.length() == 0) continue;

    char cmd = inString[0];
    switch (cmd) {
      case 'o':
      case 'n': {
        // Handle OK/NG configuration commands
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          String subCmd = inString.substring(2, commandIndex);
          int value = inString.substring(commandIndex + 1).toInt();
          
          if (cmd == 'o') {
            if (subCmd == "od") {
              ok_offset_delay = MS_TO_PULSES(value);
              EEPROM.write(EEPROM_OK_OFFSET_DELAY, value);
            } else if (subCmd == "dd") {
              ok_debounce_delay = MS_TO_PULSES(value);
              EEPROM.write(EEPROM_OK_DEBOUNCE_DELAY, value);
              updateDebounceThresholds();
            } else if (subCmd == "dp") {
              ok_debounce_percent = value;
              EEPROM.write(EEPROM_OK_DEBOUNCE_PERCENT, ok_debounce_percent);
              updateDebounceThresholds();
            }
          } else { // cmd == 'n'
            if (subCmd == "od") {
              ng_offset_delay = MS_TO_PULSES(value);
              EEPROM.write(EEPROM_NG_OFFSET_DELAY, value);
            } else if (subCmd == "dd") {
              ng_debounce_delay = MS_TO_PULSES(value);
              EEPROM.write(EEPROM_NG_DEBOUNCE_DELAY, value);
              updateDebounceThresholds();
            } else if (subCmd == "dp") {
              ng_debounce_percent = value;
              EEPROM.write(EEPROM_NG_DEBOUNCE_PERCENT, ng_debounce_percent);
              updateDebounceThresholds();
            }
          }
        }
        break;
      }

      case 's': {
        // Handle print mode setting
        if (inString == "s,l") {
          print_mode = 'l';
          EEPROM.write(EEPROM_PRINT_MODE, print_mode);
        } else if (inString == "s,n") {
          print_mode = 'n';
          EEPROM.write(EEPROM_PRINT_MODE, print_mode);
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
            EEPROM.write(EEPROM_DOWNTIME_THRESHOLD, downtime_threshold);
          }
        }
        break;
      }

      case 'e': {
        // Handle external reset relay control
        if (inString == "e,on") {
          ext_reset_enabled = true;
          EEPROM.write(EEPROM_EXT_RESET_ENABLED, 1);
        } else if (inString == "e,off") {
          ext_reset_enabled = false;
          EEPROM.write(EEPROM_EXT_RESET_ENABLED, 0);
        }
        break;
      }

      case 'r': {
        // Handle baud rate setting
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          unsigned long new_baud = inString.substring(commandIndex + 1).toInt();
          // Only allow standard baud rates
          if (new_baud == 9600 || new_baud == 19200 || new_baud == 38400 || 
              new_baud == 57600 || new_baud == 115200) {
            EEPROM.write(EEPROM_BAUD_RATE, new_baud);
            // Baud rate will take effect after reset
            resetFunc();
          }
        }
        break;
      }

      case 'v': {
        // Handle verbose mode setting
        int commandIndex = inString.indexOf(',');
        if (commandIndex != -1) {
          int value = inString.substring(commandIndex + 1).toInt();
          verbose_mode = (value == 1);
          EEPROM.write(EEPROM_VERBOSE_MODE, verbose_mode);
        }
        break;
      }

      default:
        break;
    }
  }

  printInfo();
  
  // Update pulse per second speed
  if (current_pulses - last_speed_calc_pulses >= ONE_SEC_PULSES) { 
    pulse_sec_speed = (encoder_counter - last_encoder_count); // Pulses per second (PPS)
    last_encoder_count = encoder_counter;
    last_speed_calc_pulses = current_pulses;
  }

  // Update pulse per minute speed
  if (current_pulses - last_speed_calc_minute_pulses >= ONE_SEC_PULSES * downtime_threshold) { 
    pulse_min_speed = (encoder_counter - last_encoder_count_minute) * (downtime_threshold > 0 ? (60 / downtime_threshold) : 1); // Pulses per minute
    last_encoder_count_minute = encoder_counter;
    last_speed_calc_minute_pulses = current_pulses;
    if (pulse_sec_speed == 0) {
      downtime_seconds += downtime_threshold;
    }
  }

  // Handle heart beat logic based on battery and counter sum
  if ((battery > 100 && battery < 800) || counter_sum_ok_ng > counter_rpi_reboot / 2) {
    digitalWrite(PIN_HEARTBEAT_LED, HIGH);
  } else {
    digitalWrite(PIN_HEARTBEAT_LED, LOW);
  }

  // Handle RPI reset functionality only if external reset is enabled
  if (ext_reset_enabled) {
    counter_a_b = counter_ok + counter_ng;

    if (counter_a_b > counter_rpi_reboot) {
      // Check if enough time has passed since last restart
      if (current_pulses - last_restart_pulses >= MIN_RESTART_INTERVAL) {
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
        
        last_restart_pulses = current_pulses;
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
  if (print_mode == 'n') {
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
      Serial.print("OFD:"); Serial.print(ok_offset_delay * 10 / TEN_MS_PULSES); Serial.print(",");
      Serial.print("ODD:"); Serial.print(ok_debounce_delay * 10 / TEN_MS_PULSES); Serial.print(",");
      Serial.print("ODP:"); Serial.print(ok_debounce_percent); Serial.print(",");
      Serial.print("NFD:"); Serial.print(ng_offset_delay * 10 / TEN_MS_PULSES); Serial.print(",");
      Serial.print("NDD:"); Serial.print(ng_debounce_delay * 10 / TEN_MS_PULSES); Serial.print(",");
      Serial.print("NDP:"); Serial.print(ng_debounce_percent); Serial.print(",");
      Serial.print("EXT:"); Serial.print(ext_reset_enabled ? "1" : "0"); Serial.print(",");
      Serial.print("BAUD:"); Serial.print(EEPROM.read(EEPROM_BAUD_RATE));
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


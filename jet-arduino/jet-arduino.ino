#include <avr/wdt.h>

// read documenation of indicators and the watcher in https://monitait.com/docs

const unsigned long ONE_SEC_PULSES = 125000; // Number of pulses in one second

const byte input_ok = 2; // OK
const byte input_ng = 3; // NG
const int UP_PIN = 6;
const int DOWN_PIN = 5;
const byte piPin = 11; // RPI Signal to Arduino
const byte ok_or_ng = 18; // RPI Address to Arduino
const byte warning_pin = 10; // warning LED Panel
const byte heart_beat = 13; // Heart Icon on LED Panel
const byte rpi_off = 12; // To force restart RPI by Arduino
const byte ok_identifier = 8; // RPI Address to Arduino
const byte ng_identifier = 9; // RPI Address to Arduino

byte input_pins[3] = {
  14, 15, 16
}; // RPI data pins to Arduino

byte output_pins[3] = {
  4, 7, 17
}; // Arduino data pins to RPI

long counter_ok = 0;
long counter_ng = 0;
long encoder_counter = 0; // need 100nf cap instead of 1uf in optocouplers
unsigned int battery;
unsigned int analog= 0; 
unsigned int e = 0; // extra analog read on A7
unsigned int i = 0; // counter for serial print
unsigned int counter_rpi_reboot = 1000;
unsigned int restart_counter = 1;
long counter_sum_ok_ng = 0;
unsigned long elapsed_speed=100;
volatile long a_capture_time=millis();
volatile long b_capture_time=millis();
unsigned long now_millis;
unsigned long last_pi_ping_time;
unsigned long timeout_threshold = 100000;
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

void setup() {
  wdt_enable(WDTO_8S);  // 8 second timeout
  Serial.begin(57600);
  Serial.setTimeout(100); // Add timeout for serial operations
  for(int i = 0; i < 3; i++){
    pinMode(input_pins[i], INPUT_PULLUP);
    pinMode(output_pins[i],OUTPUT);
  }
  
  pinMode(input_ok, INPUT);
  pinMode(input_ng, INPUT);
  pinMode(ok_or_ng, INPUT_PULLUP);
  pinMode(piPin, INPUT_PULLUP);

  pinMode(ok_identifier, OUTPUT);
  pinMode(ng_identifier, OUTPUT);
  pinMode(rpi_off, OUTPUT);
  pinMode(heart_beat, OUTPUT);
  pinMode(warning_pin, OUTPUT);
  digitalWrite(warning_pin, HIGH);
  
  attachInterrupt(digitalPinToInterrupt(input_ok), count_up_a, RISING);
  attachInterrupt(digitalPinToInterrupt(input_ng), count_up_b, RISING);

  TCCR0B = TCCR0B & B11111000 | B00000001; // for PWM frequency of 62500.00 Hz/ B and U outputs
}

void loop() {
  // Reset watchdog at the start of each loop
  wdt_reset();
  
  handleSerialAndAnalogData();
  
  // Add timeout protection for RPI communication
  if (digitalRead(piPin)==LOW){
    last_pi_ping_time = millis();
    restart_counter = 1;
    counter_sum_ok_ng = 0;
    digitalWrite(heart_beat, !digitalRead(heart_beat));
    get_byte = 0;
    for(int i = 0; i < 3; i++){
      if(digitalRead(input_pins[i]) == 1)
        bitSet(get_byte, i);
      else
        bitClear(get_byte, i);
    }
    bitClear(get_byte, 3); bitClear(get_byte, 4); bitClear(get_byte, 5); bitClear(get_byte, 6); bitClear(get_byte, 7);
    if(digitalRead(ok_or_ng)==LOW){
      counter_ng = counter_ng - get_byte;
    }
    else{
      counter_ok = counter_ok - get_byte;
    }
    while (digitalRead(piPin)==LOW){
      digitalWrite(ok_identifier, LOW);
      digitalWrite(ng_identifier, LOW);
      delay(1);
      handleSerialAndAnalogData();
    }
  }
  else {
    if (counter_ok > 0){
      digitalWrite(ok_identifier, HIGH);
      digitalWrite(ng_identifier, LOW);
      if (counter_ok < 8)
        out_pins_number = counter_ok % 8;
      else if (counter_ok >= 7)
        out_pins_number = 7;
      put_byte_on_pins(out_pins_number);
      delay(5);  
    }

    else if (counter_ng > 0){
      digitalWrite(ok_identifier, LOW);
      digitalWrite(ng_identifier, HIGH);
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
        digitalWrite(ok_identifier, HIGH);
        digitalWrite(ng_identifier, HIGH);
        put_byte_on_pins(out_pins_number);
      }
      else{
        out_pins_number = int(analog/132) ;
        digitalWrite(ok_identifier, LOW);
        digitalWrite(ng_identifier, LOW);
        put_byte_on_pins(out_pins_number);
      }
      delay(5); 
    }

  }
      
  delay(1);
  
}

void put_byte_on_pins(byte in_byte){
  for(int i = 0; i < 3; i++){
      digitalWrite(output_pins[i], bitRead (in_byte, i));
    }
  return;
}

void count_up_a(){
  int j = 0;  
  for(int i = 0; i < 3; i++){
    delay(1);
    if (digitalRead(input_ok) == HIGH){
      j++;
    }
  }
  if (j > 2){
    a_capture_time = millis();
    counter_ok++;
    if (digitalRead(input_ng) == HIGH)
      encoder_counter--;
    else
      encoder_counter++;  
  }  
  return;
}

void count_up_b(){
  int j = 0;  
  for(int i = 0; i < 3; i++){
    delay(1);
    if (digitalRead(input_ng) == HIGH){
      j++;
    }
  }
  if (j > 2){
    b_capture_time = millis();
    counter_ng++;
    if (digitalRead(input_ok) == HIGH)
      encoder_counter++;
    else
      encoder_counter--;
  }  
  return;
}

void handleSerialAndAnalogData() {
  // Get analog data
  battery = analogRead(A6);  
  analog = analogRead(A7);
  i++;

  if (Serial.available() > 0) {
    // Read the incoming byte with timeout
    String inString = Serial.readStringUntil('\n');
    if (inString.length() == 0) return; // Skip if no data received
    
    char inChar = inString[0];

    // Handle the command based on the received character
    switch (inChar) {
      case '1':
        analogWrite(UP_PIN, 255 - pwmup);
        analogWrite(DOWN_PIN, 255);
        updateOutputStatus(1, 0, -1);
        break;

      case '2':
        analogWrite(UP_PIN, 255);
        analogWrite(DOWN_PIN, 255 - pwmdown);
        updateOutputStatus(0, 1, -1);
        break;

      case '8':
        analogWrite(UP_PIN, 255);
        analogWrite(DOWN_PIN, 255);
        updateOutputStatus(0, 0, -1);
        break;

      case '9':
        analogWrite(UP_PIN, 255 - pwmup);
        analogWrite(DOWN_PIN, 255 - pwmdown);
        updateOutputStatus(1, 1, -1);
        break;

      case '3':
        encoder_counter = 0;
        break;

      case 'a':
        {
          int commandIndex = inString.indexOf(',');
          if (commandIndex != -1) {
            counter_ok = counter_ok - inString.substring(commandIndex + 1).toInt();
          }
        }
        break;

      case 'b':
        {
          int commandIndex = inString.indexOf(',');
          if (commandIndex != -1) {
            counter_ng = counter_ng - inString.substring(commandIndex + 1).toInt();
          }
        }
        break;

      case 'd':
        {
          int commandIndex = inString.indexOf(',');
          if (commandIndex != -1) {
            int temp_threshold = inString.substring(commandIndex + 1).toInt();
            downtime_threshold = (temp_threshold > 0) ? temp_threshold : 10; // Default to 10 if invalid
          }
        }
        break;

      case '4':
        {
          int commandIndex = inString.indexOf(',');
          if (commandIndex != -1) {
            int temp_pwm = inString.substring(commandIndex + 1).toInt();
            pwmup = (temp_pwm >= 0 && temp_pwm <= 255) ? temp_pwm : 255;
          }
        }
        break;

      case '5':
        {
          int commandIndex = inString.indexOf(',');
          if (commandIndex != -1) {
            int temp_pwm = inString.substring(commandIndex + 1).toInt();
            pwmdown = (temp_pwm >= 0 && temp_pwm <= 255) ? temp_pwm : 255;
          }
        }
        break;

      case '7':
        digitalWrite(warning_pin, HIGH);
        updateOutputStatus(-1, -1, 1);
        break;

      case '6':
        digitalWrite(warning_pin, LOW);
        updateOutputStatus(-1, -1, 0);
        break;

      default:
        break;
    }
  }

  printInfo();

  unsigned long now_millis = millis();
  
  // Check if we need to restart the RPI
  if (now_millis - last_pi_ping_time > downtime_threshold * ONE_SEC_PULSES * restart_counter) {
    // Only restart if we have data to send (counter_ok or counter_ng > 0)
    if (counter_ok > 0 || counter_ng > 0) {
      digitalWrite(rpi_off, HIGH); // Disconnect RPI power
      delay(1000); // Wait 1 second before reconnecting power
      digitalWrite(rpi_off, LOW); // Reconnect RPI power
      
      restart_counter++; // Increase restart counter
      if (restart_counter > 10) { // Limit maximum restarts
        restart_counter = -1;
      }
    }
  }

  // Update pulse per second speed
  if (now_millis - last_speed_calc_time >= ONE_SEC_PULSES) { 
    pulse_sec_speed = (encoder_counter - last_encoder_count); // Pulses per second (PPS)
    last_encoder_count = encoder_counter;
    last_speed_calc_time = now_millis;
  }

  // Update pulse per minute speed
  if (now_millis - last_speed_calc_time_minute >= ONE_SEC_PULSES*downtime_threshold) { 
    pulse_min_speed = (encoder_counter - last_encoder_count_minute) * (downtime_threshold > 0 ? (60 / downtime_threshold) : 1); // Pulses per minute (1 min)
    last_encoder_count_minute = encoder_counter;
    last_speed_calc_time_minute = now_millis;
    if (pulse_sec_speed == 0) {
      downtime_seconds += downtime_threshold;
    }
  }

  // Handle heart beat logic based on battery and counter sum
  if ((battery > 100 && battery < 800) || counter_sum_ok_ng > counter_rpi_reboot / 2) {
    digitalWrite(heart_beat, HIGH);
  } else {
    digitalWrite(heart_beat, LOW);
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
  Serial.print("ENC:"); Serial.print(encoder_counter); Serial.print(",");
  Serial.print("OKC:"); Serial.print(counter_ok); Serial.print(",");
  Serial.print("NGC:"); Serial.print(counter_ng); Serial.print(",");
  Serial.print("PPS:"); Serial.print(pulse_sec_speed); Serial.print(",");
  Serial.print("PPM:"); Serial.print(pulse_min_speed); Serial.print(",");
  Serial.print("DWS:"); Serial.print(downtime_seconds); Serial.print(",");
  Serial.print("ANG:"); Serial.print(analog); Serial.print(",");
  Serial.print("PWR:"); Serial.print(battery); Serial.print(",");
  Serial.print("STS:"); Serial.print(output_status); Serial.print(",");  // Added output status
  Serial.print("\n");
  wdt_reset();
}


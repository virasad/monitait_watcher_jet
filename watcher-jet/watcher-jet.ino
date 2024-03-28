#include <avr/wdt.h>

const byte input_a = 2; // OK
const byte input_b = 3; // NG
const byte piPin = 11; // RPI Signal to Arduino
const byte a_or_b = 18; // RPI Address to Arduino
const byte Warning = 13; // Warning LED Panel
const byte DataCapture = 10; // Link LED Panel
const byte rpi_off = 12; // To force restart RPI by Arduino
const byte a_identifier = 8; // RPI Address to Arduino
const byte b_identifier = 9; // RPI Address to Arduino

byte input_pins[4] = {
  14, 15, 16, 17
}; // RPI data pins to Arduino

byte output_pins[4] = {
  4, 5, 6, 7
}; // Arduino data pins to RPI

long counter_a = 0;
long counter_b = 0;
unsigned int battery;
unsigned int c = 0; 
unsigned int e = 0; // extra analog read on A7
unsigned int i = 0; // counter for serial print
unsigned int counter_rpi_reboot = 100;
unsigned int restart_counter = 1;
long counter_a_b = 0;
unsigned long elapsed_speed=100;
volatile long a_capture_time=millis();
volatile long b_capture_time=millis();
unsigned long now_millis;

byte get_byte;
byte out_pins_number;

void(* resetFunc) (void) = 0;

void setup() {
  wdt_enable( WDTO_8S);
  Serial.begin(9600); 
  for(int i = 0; i < 4; i++){
    pinMode(input_pins[i], INPUT_PULLUP);
    pinMode(output_pins[i],OUTPUT);
  }
  
  pinMode(input_a, INPUT);
  pinMode(input_b, INPUT);
  pinMode(a_or_b, INPUT_PULLUP);
  pinMode(piPin, INPUT_PULLUP);

  pinMode(a_identifier, OUTPUT);
  pinMode(b_identifier, OUTPUT);
  pinMode(rpi_off, OUTPUT);
  pinMode(DataCapture, OUTPUT);
  pinMode(Warning, OUTPUT);
  
  attachInterrupt(digitalPinToInterrupt(input_a), count_up_a, RISING);
  attachInterrupt(digitalPinToInterrupt(input_b), count_up_b, RISING);
}

void loop() {
  // get analog data
  c = analogRead(A5);
  battery = analogRead(A6);  
  e = analogRead(A7);
  digitalWrite(DataCapture, LOW);
  i++;
  if ( i > 500){
    Serial.println(String(counter_a) + "," + String(counter_b) + "," + String(c) + "," + String(e) + "," + String(battery/10) + "," + String(elapsed_speed) + "," + String(counter_rpi_reboot) + "," + String(restart_counter));
    i = 0;
  }
  // check if RPI is signaling the ARDUINO
  if (digitalRead(piPin)==LOW){
    digitalWrite(DataCapture, HIGH);
    get_byte = 0;
    for(int i = 0; i < 4; i++){
      if(digitalRead(input_pins[i]) == 1)
        bitSet(get_byte, i);
      else
        bitClear(get_byte, i);
    }
    bitClear(get_byte, 4); bitClear(get_byte, 5); bitClear(get_byte, 6); bitClear(get_byte, 7);
    if(digitalRead(a_or_b)==LOW){
      counter_b = counter_b - get_byte;
    }
    else{
      counter_a = counter_a - get_byte;
    }
    while (digitalRead(piPin)==LOW){
      digitalWrite(a_identifier, LOW);
      digitalWrite(b_identifier, LOW);
      delay(5);
      wdt_reset();
      
    }
  }
  else {
    if (counter_a > 0){
      digitalWrite(a_identifier, HIGH);
      digitalWrite(b_identifier, LOW);
      if (counter_a < 16)
        out_pins_number = counter_a % 16;
      else if (counter_a >= 16)
        out_pins_number = 15;
      put_byte_on_pins(out_pins_number);
      delay(5);  
    }

    else if (counter_b > 0){
      digitalWrite(a_identifier, LOW);
      digitalWrite(b_identifier, HIGH);
      if (counter_b < 16)
        out_pins_number = counter_b % 16;
      else if (counter_b >= 16)
        out_pins_number = 15;
      put_byte_on_pins(out_pins_number);
      delay(5);   
    }

    else if (counter_a + counter_b <= 0){
      if (battery < 780){
        out_pins_number = int(battery/66) ;
        digitalWrite(a_identifier, HIGH);
        digitalWrite(b_identifier, HIGH);
        put_byte_on_pins(out_pins_number);
      }
      else{
        out_pins_number = int(c/66) ;
        digitalWrite(a_identifier, LOW);
        digitalWrite(b_identifier, LOW);
        put_byte_on_pins(out_pins_number);
      }
      delay(5); 
    }

  }
  
  now_millis = millis();
  elapsed_speed =  long(80/(now_millis - a_capture_time) + 20/(now_millis - b_capture_time) + elapsed_speed*999/1000) ;
  counter_rpi_reboot = (elapsed_speed+100)*restart_counter;
  counter_a_b = abs(counter_a + counter_b);
  if (battery < 800 or counter_a_b > counter_rpi_reboot/2)
    digitalWrite(Warning, HIGH);
  else
    digitalWrite(Warning, LOW);

      
  if (counter_a_b > counter_rpi_reboot){
    digitalWrite(rpi_off, HIGH);
    delay(1000);
    digitalWrite(rpi_off, LOW);
    if (restart_counter < 500){
        restart_counter = restart_counter * 2;
        counter_rpi_reboot = (elapsed_speed+100)*restart_counter;
      }
    else{
        restart_counter = 500;
        resetFunc();
        }
    delay(1000);
  }
  
  if ((counter_a_b < counter_rpi_reboot/100) and (restart_counter > 2)){
    restart_counter = restart_counter/2;
  }
  
  delay(1);
  wdt_reset();
}

void put_byte_on_pins(byte in_byte){
  for(int i = 0; i < 4; i++){
      digitalWrite(output_pins[i], bitRead (in_byte, i));
    }
  return;
}

void count_up_a(){
  int j = 0;  
  for(int i = 0; i < 6; i++){
    delay(1);
    if (digitalRead(input_a) == HIGH)
      j++;
  }
  if (j > 4){
    a_capture_time = millis();
    counter_a++;
  }  
  return;
}

void count_up_b(){
  int j = 0;  
  for(int i = 0; i < 6; i++){
    delay(1);
    if (digitalRead(input_b) == HIGH)
      j++;
  }
  if (j > 4){
    b_capture_time = millis();
    counter_b++;
  }  
  return;
}

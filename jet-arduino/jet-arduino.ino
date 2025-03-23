#include <avr/wdt.h>

// read documenation of indicators and the watcher in https://monitait.com/docs

const byte input_ok = 2; // OK
const byte input_ng = 3; // NG
const int UP_PIN = 6;
const int DOWN_PIN = 5;
const byte piPin = 11; // RPI Signal to Arduino
const byte ok_or_ng = 18; // RPI Address to Arduino
const byte warning = 10; // warning LED Panel
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


byte get_byte;
byte out_pins_number;

void(* resetFunc) (void) = 0;

void setup() {
  wdt_enable( WDTO_8S);
  Serial.begin(57600); 
  for(int i = 0; i < 4; i++){
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
  pinMode(warning, OUTPUT);
  digitalWrite(warning, HIGH);
  
  attachInterrupt(digitalPinToInterrupt(input_ok), count_up_a, RISING);
  attachInterrupt(digitalPinToInterrupt(input_ng), count_up_b, RISING);

  TCCR0B = TCCR0B & B11111000 | B00000001; // for PWM frequency of 62500.00 Hz/ B and U outputs
}

void loop() {
  // get analog data
  battery = analogRead(A6);  
  analog= analogRead(A7);
  i++;

if (Serial.available() > 0)
  {
//    // read the incoming byte:
    String inString = Serial.readStringUntil('\n');
    char inChar=inString[0];
//    // say what you got:
    switch (inChar){
      case '1':
        {analogWrite(UP_PIN, 255-pwmup);
        analogWrite(DOWN_PIN, 255);}
        break;

      case '2':
        {analogWrite(UP_PIN, 255);
        analogWrite(DOWN_PIN, 255-pwmdown);}
        break;

      case '8':
        {analogWrite(UP_PIN, 255);
        analogWrite(DOWN_PIN, 255);}
        break;

      case '3':
        {encoder_counter=0;}
        break;

      case 'a':
        {int commandIndex = inString.indexOf(',');
        if (commandIndex != -1){counter_ok = counter_ok - inString.substring(commandIndex +1).toInt();}}
        break;

      case 'b':
        {int commandIndex = inString.indexOf(',');
        if (commandIndex != -1){counter_ng = counter_ng - inString.substring(commandIndex +1).toInt();}}
        break;

      case '4':
        {int commandIndex = inString.indexOf(',');
        if (commandIndex != -1){pwmup = inString.substring(commandIndex +1).toInt();}}
        break;

      case '5':
        {int commandIndex = inString.indexOf(',');
        if (commandIndex != -1){pwmdown = inString.substring(commandIndex +1).toInt();}}
        break;

      case '7':
        {digitalWrite(warning, HIGH);}
        break;

      case '6':
        {digitalWrite(warning, LOW);}
        break;
    
      default: 
        break;
      }
    }


  printInfo(encoder_counter, counter_ok, counter_ng, elapsed_speed, analog);
  // check if RPI is signaling the ARDUINO
  if (digitalRead(piPin)==LOW){
    last_pi_ping_time = millis();
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
      printInfo(encoder_counter, counter_ok, counter_ng, elapsed_speed, analog);
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
  
  now_millis = millis();
  if (now_millis - last_pi_ping_time > timeout_threshold*restart_counter){
    //restart rpi
  } 
  elapsed_speed =  long(50/(now_millis - a_capture_time) + 50/(now_millis - b_capture_time) + elapsed_speed*999/1000) ;
  counter_rpi_reboot = (elapsed_speed+1000)*restart_counter;
  counter_sum_ok_ng = (999*counter_sum_ok_ng + abs(counter_ok + counter_ng))/1000;
  if ((battery > 100 and battery < 800) or counter_sum_ok_ng > counter_rpi_reboot/2)
    digitalWrite(heart_beat, HIGH);
  else
    digitalWrite(heart_beat, LOW);
      
  // if (counter_sum_ok_ng > counter_rpi_reboot){
  //   digitalWrite(rpi_off, HIGH);
  //   delay(1000);
  //   digitalWrite(rpi_off, LOW);
  //   if (restart_counter < 500){
  //       restart_counter = restart_counter * 2;
  //       counter_rpi_reboot = (elapsed_speed+1000)*restart_counter;
  //     }
  //   else{
  //       restart_counter = 499;
  //       resetFunc();
  //       }
  //   delay(1000);
  // }
  
  // if ((counter_sum_ok_ng < counter_rpi_reboot/100) and (restart_counter > 2)){
  //   restart_counter = restart_counter/2;
  // }
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

void printInfo(int encoder_counter, int counter_ok, int counter_ng, int elapsed_speed, int analog) {
  Serial.print("Encoder:"); Serial.print(encoder_counter); Serial.print(",");
  Serial.print("Red:"); Serial.print(counter_ok); Serial.print(",");
  Serial.print("Green:"); Serial.print(counter_ng); Serial.print(",");
  Serial.print("Blue:"); Serial.print(elapsed_speed); Serial.print(",");
  Serial.print("Color:"); Serial.print(analog); Serial.print(",");
  Serial.print("\n");
  wdt_reset();
}
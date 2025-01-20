#include <avr/wdt.h>

const byte input_a = 2; // OK
const byte input_b = 3; // NG
const int UP_PIN = 6;
const int DOWN_PIN = 5;
const byte piPin = 11; // RPI Signal to Arduino
const byte a_or_b = 18; // RPI Address to Arduino
const byte Ejector = 10; // Motor (warning) LED Panel
const byte DataCapture = 13; // Link LED Panel
const byte rpi_off = 12; // To force restart RPI by Arduino
const byte a_identifier = 8; // RPI Address to Arduino
const byte b_identifier = 9; // RPI Address to Arduino

byte input_pins[3] = {
  14, 15, 16
}; // RPI data pins to Arduino

byte output_pins[3] = {
  4, 7, 17
}; // Arduino data pins to RPI

boolean old_a;
boolean old_b;
long counter_a = 0;
long counter_b = 0;
long encoder_counter = 0; // need 100nf cap instead of 1uf in optocouplers
unsigned int battery;
unsigned int c = 0; 
unsigned int e = 0; // extra analog read on A7
unsigned int i = 0; // counter for serial print
unsigned int counter_rpi_reboot = 1000;
unsigned int restart_counter = 1;
long counter_a_b = 0;
unsigned long elapsed_speed=100;
volatile long a_capture_time=millis();
volatile long b_capture_time=millis();
unsigned long now_millis;
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
  
  pinMode(input_a, INPUT);
  pinMode(input_b, INPUT);
  pinMode(a_or_b, INPUT_PULLUP);
  pinMode(piPin, INPUT_PULLUP);

  pinMode(a_identifier, OUTPUT);
  pinMode(b_identifier, OUTPUT);
  pinMode(rpi_off, OUTPUT);
  pinMode(DataCapture, OUTPUT);
  pinMode(Ejector, OUTPUT);
  
  attachInterrupt(digitalPinToInterrupt(input_a), count_up_a, RISING);
  attachInterrupt(digitalPinToInterrupt(input_b), count_up_b, RISING);

  TCCR0B = TCCR0B & B11111000 | B00000001; // for PWM frequency of 62500.00 Hz/ B and U outputs
}

void loop() {
  // get analog data
  battery = analogRead(A6);  
  c = analogRead(A7);
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
        if (commandIndex != -1){counter_a = counter_a - inString.substring(commandIndex +1).toInt();}}
        break;

      case 'b':
        {int commandIndex = inString.indexOf(',');
        if (commandIndex != -1){counter_b = counter_b - inString.substring(commandIndex +1).toInt();}}
        break;

      case '4':
        {int commandIndex = inString.indexOf(',');
        if (commandIndex != -1){pwmup = inString.substring(commandIndex +1).toInt();}}
        break;

      case '5':
        {int commandIndex = inString.indexOf(',');
        if (commandIndex != -1){pwmdown = inString.substring(commandIndex +1).toInt();}}
        break;

      case '6':
        {digitalWrite(Ejector, HIGH);}
        break;

      case '7':
        {digitalWrite(Ejector, LOW);}
        break;
        

      default: 
      break;
      }
    
    
    }

  
  // if ( i > 1){
  //   Serial.println(String(encoder_counter) + "," + "-24" + "," + String(counter_a) + "," + String(counter_b) + "," + String(c) + "," + String(battery/10 - 2) + "," + String(elapsed_speed) + "," + String(restart_counter));
  //   i = 0;
  // }

  Serial.print("Encoder:"); Serial.print(encoder_counter); Serial.print(",");
  Serial.print("Red:0,");
  Serial.print("Green:0,");
  Serial.print("Blue:0,");
  Serial.print("Color:0, ");
  Serial.print("\n");
  
  // check if RPI is signaling the ARDUINO
  if (digitalRead(piPin)==LOW){
    wdt_reset();
    counter_a_b = 0;
    digitalWrite(DataCapture, !digitalRead(DataCapture));
    get_byte = 0;
    for(int i = 0; i < 3; i++){
      if(digitalRead(input_pins[i]) == 1)
        bitSet(get_byte, i);
      else
        bitClear(get_byte, i);
    }
    bitClear(get_byte, 3); bitClear(get_byte, 4); bitClear(get_byte, 5); bitClear(get_byte, 6); bitClear(get_byte, 7);
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
      Serial.print("Encoder:"); Serial.print(encoder_counter); Serial.print(",");
      Serial.print("Red:0,");
      Serial.print("Green:0,");
      Serial.print("Blue:0,");
      Serial.print("Color:0,");
      Serial.print("\n");
      wdt_reset();      
    }
  }
  else {
    if (counter_a > 0){
      digitalWrite(a_identifier, HIGH);
      digitalWrite(b_identifier, LOW);
      if (counter_a < 8)
        out_pins_number = counter_a % 8;
      else if (counter_a >= 7)
        out_pins_number = 7;
      put_byte_on_pins(out_pins_number);
      delay(5);  
    }

    else if (counter_b > 0){
      digitalWrite(a_identifier, LOW);
      digitalWrite(b_identifier, HIGH);
      if (counter_b < 16)
        out_pins_number = counter_b % 8;
      else if (counter_b >= 7)
        out_pins_number = 7;
      put_byte_on_pins(out_pins_number);
      delay(5);   
    }

    else if (counter_a + counter_b <= 0){
      if (battery < 780){
        out_pins_number = int(battery/132) ;
        digitalWrite(a_identifier, HIGH);
        digitalWrite(b_identifier, HIGH);
        put_byte_on_pins(out_pins_number);
      }
      else{
        out_pins_number = int(c/132) ;
        digitalWrite(a_identifier, LOW);
        digitalWrite(b_identifier, LOW);
        put_byte_on_pins(out_pins_number);
      }
      delay(5); 
    }

  }
  
  now_millis = millis();
  elapsed_speed =  long(50/(now_millis - a_capture_time) + 50/(now_millis - b_capture_time) + elapsed_speed*999/1000) ;
  counter_rpi_reboot = (elapsed_speed+1000)*restart_counter;
  counter_a_b = (999*counter_a_b + abs(counter_a + counter_b))/1000;
  if ((battery > 100 and battery < 800) or counter_a_b > counter_rpi_reboot/2)
    digitalWrite(DataCapture, HIGH);
  else
    digitalWrite(DataCapture, LOW);
      
  // if (counter_a_b > counter_rpi_reboot){
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
  
  // if ((counter_a_b < counter_rpi_reboot/100) and (restart_counter > 2)){
  //   restart_counter = restart_counter/2;
  // }
  
  delay(1);
  wdt_reset();
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
    if (digitalRead(input_a) == HIGH){
      j++;
    }
  }
  if (j > 2){
    a_capture_time = millis();
    counter_a++;
    if (digitalRead(input_b) == HIGH)
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
    if (digitalRead(input_b) == HIGH){
      j++;
    }
  }
  if (j > 2){
    b_capture_time = millis();
    counter_b++;
    if (digitalRead(input_a) == HIGH)
      encoder_counter++;
    else
      encoder_counter--;
  }  
  return;
}

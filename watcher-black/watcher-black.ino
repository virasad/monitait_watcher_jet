const byte ledPin = 13;
const byte sensorPin = 2;
const byte piPin = 3;
const byte DataCapture = 12;
byte input_pins[5] = {
  14, 15, 16, 17, 18
};

byte output_pins[6] = {
  4, 5, 6, 7, 8, 9
};

volatile byte state = LOW;
volatile byte data_state = LOW;
long counter = 0;
byte out_pins_number;
void setup() {
  Serial.begin(9600); 
  for(int i = 0; i < 5; i++){
    pinMode(input_pins[i], INPUT_PULLUP);
    pinMode(output_pins[i],OUTPUT);
  }
  pinMode(output_pins[5],OUTPUT);
  pinMode(sensorPin, INPUT);
  
  pinMode(ledPin, OUTPUT);
  pinMode(DataCapture, OUTPUT);
  pinMode(piPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(sensorPin), count_up, RISING);
  attachInterrupt(digitalPinToInterrupt(piPin), sub_down, RISING);
}

void loop() {
  digitalWrite(ledPin, state);
  digitalWrite(DataCapture, data_state);
  if (counter >= 0 and counter < 32)
    out_pins_number = counter % 32;
  else if (counter >= 32)
    out_pins_number = 31;
  else if (counter < 0){
    counter = 0;
    out_pins_number = 0;
    }
  else
    out_pins_number = 0;
  put_byte_on_pins(out_pins_number);
  Serial.print(counter);
  Serial.print(",");
  Serial.println(int(out_pins_number));
  delay(100);
}

void put_byte_on_pins(byte in_byte){
  for(int i = 0; i < 5; i++){
      digitalWrite(output_pins[i], bitRead (in_byte, i));
    }
  return;
}

void count_up(){
//  int j = 0;
  counter++;
//  for(int i = 0; i < 6; i++){
//    delay(1);
//    if (digitalRead(sensorPin) == HIGH)
//      j++;
//  }
//  if (j > 4){
//    counter++;
    state = !state;
//  }  
  return;
}

void sub_down(){
  
  byte get_byte = 0;
  for(int i = 0; i < 5; i++){
    if(digitalRead(input_pins[i]) == 1)
      bitSet(get_byte, i);
    else
      bitClear(get_byte, i);
  }
  bitClear(get_byte, 5);
  bitClear(get_byte, 6);
  bitClear(get_byte, 7);
  Serial.println(get_byte);
  counter = counter - get_byte;
  data_state = !data_state;
  return;
}

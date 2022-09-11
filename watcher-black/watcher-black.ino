const byte ledPin = 13;
const byte sensorPin = 2;
const byte piPin = 3;

byte input_pins[5] = {
  14, 15, 16, 17, 18
};

byte output_pins[6] = {
  4, 5, 6, 7, 8, 9
};

volatile byte state = LOW;
long counter = 0;
byte out_pins_number;
void setup() {
  Serial.begin(9600); 
  for(int i = 0; i < 5; i++){
    pinMode(input_pins[i], INPUT_PULLUP);
    pinMode(output_pins[i],OUTPUT);
  }
  pinMode(output_pins[6],OUTPUT);
  pinMode(sensorPin, INPUT_PULLUP);
  
  pinMode(ledPin, OUTPUT);
  pinMode(sensorPin, INPUT_PULLUP);
  pinMode(piPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(sensorPin), count_up, RISING);
  attachInterrupt(digitalPinToInterrupt(piPin), sub_down, FALLING);
}

void loop() {
  digitalWrite(ledPin, state);
  if (counter >= 0 and counter < 64)
    out_pins_number = counter % 64;
  else if (counter >= 64)
    out_pins_number = 63;
  else
    out_pins_number = 0;
  put_byte_on_pins(out_pins_number);
  Serial.print(counter);
  Serial.print(",");
  Serial.println(int(out_pins_number));
  delay(100);
}

void put_byte_on_pins(byte in_byte){
  for(int i = 0; i < 6; i++){
      digitalWrite(output_pins[i], bitRead (in_byte, i));
    }
  return;
}

void count_up(){
  counter++;
  state = !state;
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
  state = !state;
  digitalWrite(ledPin, state);
  delay(200);
  state = !state;
  return;
}

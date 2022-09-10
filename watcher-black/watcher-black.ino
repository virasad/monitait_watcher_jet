const byte ledPin = 13;
const byte sensorPin = 2;
const byte piPin = 3;

byte input_pins[7] = {
  12, 14, 15, 16, 17, 18, 19
};

byte output_pins[7] = {
  4, 5, 6, 7, 8, 9, 10
};

volatile byte state = LOW;
long counter = 0;
byte out_pins_number;
void setup() {
  Serial.begin(9600); 
  for(int i = 0; i < 7; i++){
    pinMode(input_pins[i], INPUT_PULLUP);
    pinMode(output_pins[i],OUTPUT);
  }
  pinMode(sensorPin, INPUT_PULLUP);
  
  pinMode(ledPin, OUTPUT);
  pinMode(sensorPin, INPUT_PULLUP);
  pinMode(piPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(sensorPin), count_up, RISING);
  attachInterrupt(digitalPinToInterrupt(piPin), sub_down, FALLING);
}

void loop() {
  digitalWrite(ledPin, state);
  if (counter >= 0 and counter < 128)
    out_pins_number = counter % 128;
  else if (counter >= 128)
    out_pins_number = 127;
  else
    out_pins_number = 0;
  put_byte_on_pins(out_pins_number);
  Serial.print(counter);
  Serial.print(",");
  Serial.println(int(out_pins_number));
  delay(100);
}

void put_byte_on_pins(byte in_byte){
  for(int i = 0; i < 7; i++){
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
  byte get_byte = B00000000;
  for(int i = 0; i < 7; i++)
  {
    if(digitalRead(input_pins[i]) == 1)
      bitSet(get_byte, i);
  }
  counter = counter - get_byte;
  put_byte_on_pins(B00000000);
  state = !state;
  digitalWrite(ledPin, state);
  delay(1000);
  state = !state;
  return;
}

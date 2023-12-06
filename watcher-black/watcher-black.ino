const byte input_a = 2;
const byte input_b = 3;
const byte piPin = 11;
const byte a_or_b = 18;
const byte Warning = 10;
const byte DataCapture = 12;
const byte rpi_off = 13;
const byte a_identifier = 8;
const byte b_identifier = 9;

byte input_pins[4] = {
  14, 15, 16, 17
};

byte output_pins[4] = {
  4, 5, 6, 7
};

volatile byte state = LOW;
volatile byte data_state = LOW;
long counter_a = 0;
long counter_b = 0;
byte out_pins_number;
void setup() {
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
  
  if (counter_a + counter_b > 0 and counter_a + counter_b < 10000) {
    if (counter_a >= 0 and counter_a < 16)
      out_pins_number = counter_a % 16;
    else if (counter_a >= 16)
      out_pins_number = 15;
    else if (counter_a < 0){
      counter_a = 0;
      out_pins_number = 0;
      }
    else
      out_pins_number = 0;  
  }
  else if (counter_a + counter_b > 10000){
    digitalWrite(rpi_off, HIGH);
    delay(10000)
    digitalWrite(rpi_off, LOW);
    counter_a = 0
    counter_b = 0
  }
  
  c = analogRead(A5)
  battery = analogRead(A6)
  if (battery < 800)
    digitalWrite(warning, HIGH);
  else
    digitalWrite(warning, LOW);
  
  digitalWrite(DataCapture, data_state);

  put_byte_on_pins(out_pins_number);
  Serial.print("a: ");
  Serial.print(counter_a);
  Serial.print(",b: ");
  Serial.print(counter_b);
  Serial.print(",c: ");
  Serial.print(c);
  Serial.println(int(out_pins_number));
  delay(100);
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
    counter_a++;
    state = !state;
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
    counter_b++;
    state = !state;
  }  
  return;
}

void sub_down(){
  
  byte get_byte = 0;
  for(int i = 0; i < 4; i++){
    if(digitalRead(input_pins[i]) == 1)
      bitSet(get_byte, i);
    else
      bitClear(get_byte, i);
  }
  bitClear(get_byte, 4);
  bitClear(get_byte, 5);
  bitClear(get_byte, 6);
  bitClear(get_byte, 7);
  Serial.println(get_byte);
  counter = counter - get_byte; ####
  data_state = !data_state;
  return;
}

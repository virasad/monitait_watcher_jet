const byte input_a = 2;
const byte input_b = 3;
const byte piPin = 11;
const byte a_or_b = 18;
const byte Warning = 12;
const byte DataCapture = 10;
const byte rpi_off = 13;
const byte a_identifier = 8;
const byte b_identifier = 9;

byte input_pins[4] = {
  14, 15, 16, 17
};

byte output_pins[4] = {
  4, 5, 6, 7
};

long counter_a = 0;
long counter_b = 0;
int battery;
int c = 0;
int counter_rpi_reboot = 0;
byte get_byte;
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
  // get analog data
  c = analogRead(A5);
  battery = analogRead(A6);  
  digitalWrite(DataCapture, LOW);
  Serial.print("a: "); Serial.print(counter_a); Serial.print(",b: "); Serial.print(counter_b); Serial.print(",c: "); Serial.print(c); Serial.print(",battery: "); Serial.print(battery/10); Serial.println("%");
 
  // check if rpi informed the arduino
  if (digitalRead(piPin)==HIGH){
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
    while (digitalRead(piPin)==HIGH){
      digitalWrite(a_identifier, HIGH);
      digitalWrite(b_identifier, HIGH);
      delay(1);
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
        digitalWrite(a_identifier, LOW);
        digitalWrite(b_identifier, LOW);
        put_byte_on_pins(out_pins_number);
      }
      else{
        out_pins_number = int(c/66) ;
        digitalWrite(a_identifier, HIGH);
        digitalWrite(b_identifier, HIGH);
        put_byte_on_pins(out_pins_number);
      }
      delay(5); 
    }

  }

  if (battery < 800 or counter_a + counter_b > 500)
    digitalWrite(Warning, HIGH);
  else
    digitalWrite(Warning, LOW);
      
  if (counter_a + counter_b > 1000*(counter_rpi_reboot + 1)){
    digitalWrite(rpi_off, HIGH);
    delay(10000);
    digitalWrite(rpi_off, LOW);
    counter_rpi_reboot +=1;
    counter_a += 15; // on reboot input pins are high by default, this is for compensentation
    delay(100000);
  }
  else
    counter_rpi_reboot = 0;
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
  }  
  return;
}
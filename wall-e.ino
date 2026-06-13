#include <AFMotor.h>
#include <Servo.h>

AF_DCMotor motorRight(1);  // M1
AF_DCMotor motorLeft(2);   // M2

Servo servoRightHand;  // SERVO_1 = D9
Servo servoLeftHand;   // SERVO_2 = D10
Servo servoNeck;       // D2

#define SPEED_FULL 200
#define SPEED_TURN 160

#define NECK_CENTER  90
#define NECK_LEFT   145
#define NECK_RIGHT   35
#define HAND_REST    90
#define HAND_UP     165
#define HAND_DOWN    15

void setup() {
  Serial.begin(9600);

  motorRight.setSpeed(SPEED_FULL);
  motorLeft.setSpeed(SPEED_FULL);
  motorRight.run(RELEASE);
  motorLeft.run(RELEASE);

  servoRightHand.attach(9);
  servoLeftHand.attach(10);
  servoNeck.attach(2);

  servoNeck.write(NECK_CENTER);
  servoLeftHand.write(HAND_REST);
  servoRightHand.write(HAND_REST);
  delay(1000);

  Serial.println("=== WALLY DEMO MODE ===");
}

void stopMotors() {
  motorRight.run(RELEASE);
  motorLeft.run(RELEASE);
}

void goForward() {
  motorRight.setSpeed(SPEED_FULL);
  motorLeft.setSpeed(SPEED_FULL);
  motorRight.run(FORWARD);
  motorLeft.run(FORWARD);
}

void goBackward() {
  motorRight.setSpeed(SPEED_FULL);
  motorLeft.setSpeed(SPEED_FULL);
  motorRight.run(BACKWARD);
  motorLeft.run(BACKWARD);
}

void turnLeft() {
  motorRight.setSpeed(SPEED_TURN);
  motorLeft.setSpeed(SPEED_TURN);
  motorRight.run(FORWARD);
  motorLeft.run(BACKWARD);
}

void turnRight() {
  motorRight.setSpeed(SPEED_TURN);
  motorLeft.setSpeed(SPEED_TURN);
  motorRight.run(BACKWARD);
  motorLeft.run(FORWARD);
}

void testServos() {
  Serial.println("-- Neck left");
  servoNeck.write(NECK_LEFT);   delay(700);
  Serial.println("-- Neck right");
  servoNeck.write(NECK_RIGHT);  delay(700);
  Serial.println("-- Neck center");
  servoNeck.write(NECK_CENTER); delay(500);

  Serial.println("-- Left hand up");
  servoLeftHand.write(HAND_UP);   delay(500);
  Serial.println("-- Left hand down");
  servoLeftHand.write(HAND_DOWN); delay(500);
  Serial.println("-- Left hand rest");
  servoLeftHand.write(HAND_REST); delay(300);

  Serial.println("-- Right hand up");
  servoRightHand.write(HAND_UP);   delay(500);
  Serial.println("-- Right hand down");
  servoRightHand.write(HAND_DOWN); delay(500);
  Serial.println("-- Right hand rest");
  servoRightHand.write(HAND_REST); delay(300);

  Serial.println("-- Wave!");
  for (int i = 0; i < 3; i++) {
    servoLeftHand.write(HAND_UP);
    servoRightHand.write(HAND_UP);
    delay(250);
    servoLeftHand.write(HAND_REST);
    servoRightHand.write(HAND_REST);
    delay(250);
  }
}

void testMotors() {
  Serial.println("-- Forward");
  goForward();  delay(1000);
  Serial.println("-- Stop");
  stopMotors(); delay(500);

  Serial.println("-- Backward");
  goBackward(); delay(1000);
  Serial.println("-- Stop");
  stopMotors(); delay(500);

  Serial.println("-- Turn left");
  turnLeft();   delay(800);
  Serial.println("-- Stop");
  stopMotors(); delay(500);

  Serial.println("-- Turn right");
  turnRight();  delay(800);
  Serial.println("-- Stop");
  stopMotors(); delay(500);
}

void loop() {
  Serial.println("=== SERVO TEST ===");
  testServos();
  delay(1000);

  Serial.println("=== MOTOR TEST ===");
  testMotors();

  Serial.println("=== CYCLE DONE — pause 3s ===");
  delay(3000);
}
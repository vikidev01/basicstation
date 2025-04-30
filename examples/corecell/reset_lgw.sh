#!/bin/bash

# Este script está adaptado para Raspberry Pi 5 usando libgpiod.
# Realiza:
#  - Encendido del Corecell (GPIO18)
#  - Reset del SX1302 (GPIO17)
# Requiere: sudo apt install gpiod

SX1302_RESET_PIN=17
GPIOCHIP=gpiochip0  # Confirmado en tu sistema

WAIT_GPIO() {
    sleep 0.1
}

reset() {
    gpioset $GPIOCHIP $SX1302_RESET_PIN=0
    WAIT_GPIO
    gpioset $GPIOCHIP $SX1302_RESET_PIN=1
    WAIT_GPIO
    gpioset $GPIOCHIP $SX1302_RESET_PIN=0
    WAIT_GPIO
    
    echo "CoreCell reset a través del GPIO$SX1302_RESET_PIN..."

}

poweroff() {
    echo "Apagando el módulo CoreCell (GPIO$SX1302_POWER_EN_PIN)..."
    gpioset $GPIOCHIP $SX1302_RESET_PIN=0
}

case "$1" in
    start)
        reset
        ;;
    stop)
        poweroff
        ;;
    *)
        echo "Uso: $0 {start|stop}"
        exit 1
        ;;
esac

exit 0

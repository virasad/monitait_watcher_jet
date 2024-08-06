#!python

# Tested with `SC-8110-2D-B` 1d & 2d barcode scanner
#
# Inspired by https://github.com/julzhk/usb_barcode_scanner
# which was inspired by https://www.piddlerintheroot.com/barcode-scanner/
# https://www.raspberrypi.org/forums/viewtopic.php?f=45&t=55100
# from 'brechmos' - thank-you!
#
# This implementation doesn't directly decode hidraw stream, but uses
# evdev and grabs the device, so the code arrives only in this script
# and not in any active input window.
#
# Also, it uses a list of USB vendor:product to identify the device,
# so that you don't have to set the dev path.
#
# License: MIT No Attribution License (MIT-0) - https://opensource.org/licenses/MIT-0

import evdev
import logging

ERROR_CHARACTER = '?'
VALUE_UP = 0
VALUE_DOWN = 1

# USB VENDOR & PRODUCT list of 2d scanners
VENDOR_PRODUCT = [
        [0xac90, 0x3002], # [vendor, product]
        ]

CHARMAP = {
        evdev.ecodes.KEY_1: ['1', '!'],
        evdev.ecodes.KEY_2: ['2', '@'],
        evdev.ecodes.KEY_3: ['3', '#'],
        evdev.ecodes.KEY_4: ['4', '$'],
        evdev.ecodes.KEY_5: ['5', '%'],
        evdev.ecodes.KEY_6: ['6', '^'],
        evdev.ecodes.KEY_7: ['7', '&'],
        evdev.ecodes.KEY_8: ['8', '*'],
        evdev.ecodes.KEY_9: ['9', '('],
        evdev.ecodes.KEY_0: ['0', ')'],
        evdev.ecodes.KEY_MINUS: ['-', '_'],
        evdev.ecodes.KEY_EQUAL: ['=', '+'],
        evdev.ecodes.KEY_TAB: ['\t', '\t'],
        evdev.ecodes.KEY_Q: ['q', 'Q'],
        evdev.ecodes.KEY_W: ['w', 'W'],
        evdev.ecodes.KEY_E: ['e', 'E'],
        evdev.ecodes.KEY_R: ['r', 'R'],
        evdev.ecodes.KEY_T: ['t', 'T'],
        evdev.ecodes.KEY_Y: ['y', 'Y'],
        evdev.ecodes.KEY_U: ['u', 'U'],
        evdev.ecodes.KEY_I: ['i', 'I'],
        evdev.ecodes.KEY_O: ['o', 'O'],
        evdev.ecodes.KEY_P: ['p', 'P'],
        evdev.ecodes.KEY_LEFTBRACE: ['[', '{'],
        evdev.ecodes.KEY_RIGHTBRACE: [']', '}'],
        evdev.ecodes.KEY_A: ['a', 'A'],
        evdev.ecodes.KEY_S: ['s', 'S'],
        evdev.ecodes.KEY_D: ['d', 'D'],
        evdev.ecodes.KEY_F: ['f', 'F'],
        evdev.ecodes.KEY_G: ['g', 'G'],
        evdev.ecodes.KEY_H: ['h', 'H'],
        evdev.ecodes.KEY_J: ['j', 'J'],
        evdev.ecodes.KEY_K: ['k', 'K'],
        evdev.ecodes.KEY_L: ['l', 'L'],
        evdev.ecodes.KEY_SEMICOLON: [';', ':'],
        evdev.ecodes.KEY_APOSTROPHE: ['\'', '"'],
        evdev.ecodes.KEY_BACKSLASH: ['\\', '|'],
        evdev.ecodes.KEY_Z: ['z', 'Z'],
        evdev.ecodes.KEY_X: ['x', 'X'],
        evdev.ecodes.KEY_C: ['c', 'C'],
        evdev.ecodes.KEY_V: ['v', 'V'],
        evdev.ecodes.KEY_B: ['b', 'B'],
        evdev.ecodes.KEY_N: ['n', 'N'],
        evdev.ecodes.KEY_M: ['m', 'M'],
        evdev.ecodes.KEY_COMMA: [',', '<'],
        evdev.ecodes.KEY_DOT: ['.', '>'],
        evdev.ecodes.KEY_SLASH: ['/', '?'],
        evdev.ecodes.KEY_SPACE: [' ', ' '],
        }


def barcode_reader_evdev(dev):
    barcode_string_output = ''
    # barcode can have a 'shift' character; this switches the character set
    # from the lower to upper case variant for the next character only.
    shift_active = False
    for event in dev.read_loop():

        #print('categorize:', evdev.categorize(event))
        #print('typeof:', type(event.code))
        #print("event.code:", event.code)
        #print("event.type:", event.type)
        #print("event.value:", event.value)
        #print("event:", event)

        if event.code == evdev.ecodes.KEY_ENTER and event.value == VALUE_DOWN:
            #print('KEY_ENTER -> return')
            # all barcodes end with a carriage return
            return barcode_string_output
        elif event.code == evdev.ecodes.KEY_LEFTSHIFT or event.code == evdev.ecodes.KEY_RIGHTSHIFT:
            #print('SHIFT')
            shift_active = event.value == VALUE_DOWN
        elif event.value == VALUE_DOWN:
            ch = CHARMAP.get(event.code, ERROR_CHARACTER)[1 if shift_active else 0]
            #print('ch:', ch)
            # if the charcode isn't recognized, use ?
            barcode_string_output += ch

def get_device():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        print('device:', device)
        print('info:', device.info)
        print(device.path, device.name, device.phys)
        for vp in VENDOR_PRODUCT:
            if device.info.vendor == vp[0] and device.info.product == vp[1]:
                return device
    return None

if __name__ == '__main__':

    for path in evdev.list_devices():
        print('path:', path)

    dev = get_device()
    print('selected device:', dev)
#    dev = evdev.InputDevice('/dev/input/event4')
#    dev = evdev.InputDevice('/dev/hidraw0')
#    dev = evdev.InputDevice('/dev/input/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3:1.0-event-kbd')
#    dev = evdev.InputDevice('/dev/input/by-id/usb-SM_SM-2D_PRODUCT_HID_KBW_APP-000000000-event-kbd')
    dev.grab()

    try:
        while True:
            upcnumber = barcode_reader_evdev(dev)
            print(upcnumber)
    except KeyboardInterrupt:
        logging.debug('Keyboard interrupt')
    except Exception as err:
        logging.error(err)

    dev.ungrab()

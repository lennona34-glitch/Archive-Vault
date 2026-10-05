package org.archivevault.mobile.input

import android.view.KeyEvent
import android.view.MotionEvent
import android.webkit.WebView
import java.util.concurrent.ConcurrentHashMap

class GameInputHandler {

    private var targetWebView: WebView? = null
    private val keyStateMap = ConcurrentHashMap<Int, Boolean>()

    // Analog stick threshold tracking
    private var stickUp = false
    private var stickDown = false
    private var stickLeft = false
    private var stickRight = false

    fun bindWebView(webView: WebView?) {
        targetWebView = webView
    }

    fun unbind() {
        targetWebView = null
        keyStateMap.clear()
        stickUp = false
        stickDown = false
        stickLeft = false
        stickRight = false
    }

    fun sendJsKeyEvent(keyCode: Int, key: String, code: String, isDown: Boolean) {
        val wv = targetWebView ?: return
        val eventType = if (isDown) "keydown" else "keyup"
        val js = """
            (function() {
                var ev = new KeyboardEvent('$eventType', {
                    keyCode: $keyCode,
                    which: $keyCode,
                    key: '$key',
                    code: '$code',
                    bubbles: true,
                    cancelable: true
                });
                window.dispatchEvent(ev);
                var canvas = document.getElementById('canvas');
                if (canvas) {
                    canvas.dispatchEvent(ev);
                    canvas.focus();
                }
            })();
        """.trimIndent()
        wv.post { wv.evaluateJavascript(js, null) }
    }

    fun sendJsMouseRelative(deltaX: Float, deltaY: Float) {
        val wv = targetWebView ?: return
        val js = """
            (function() {
                var can = document.getElementById('canvas');
                if (!can) return;
                window.__av_mouse = window.__av_mouse || { x: can.width / 2, y: can.height / 2 };
                var rect = can.getBoundingClientRect();
                window.__av_mouse.x = Math.max(0, Math.min(can.width, window.__av_mouse.x + ($deltaX)));
                window.__av_mouse.y = Math.max(0, Math.min(can.height, window.__av_mouse.y + ($deltaY)));
                var clientX = rect.left + (window.__av_mouse.x / can.width) * rect.width;
                var clientY = rect.top + (window.__av_mouse.y / can.height) * rect.height;
                var ev = new MouseEvent('mousemove', {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: clientX,
                    clientY: clientY,
                    screenX: clientX,
                    screenY: clientY,
                    movementX: $deltaX,
                    movementY: $deltaY
                });
                can.dispatchEvent(ev);
            })();
        """.trimIndent()
        wv.post { wv.evaluateJavascript(js, null) }
    }

    fun sendJsMouseButton(button: Int, isDown: Boolean) {
        val wv = targetWebView ?: return
        val eventType = if (isDown) "mousedown" else "mouseup"
        val buttons = if (isDown) (if (button == 2) 2 else 1) else 0
        val js = """
            (function() {
                var can = document.getElementById('canvas');
                if (!can) return;
                window.__av_mouse = window.__av_mouse || { x: can.width / 2, y: can.height / 2 };
                var rect = can.getBoundingClientRect();
                var clientX = rect.left + (window.__av_mouse.x / can.width) * rect.width;
                var clientY = rect.top + (window.__av_mouse.y / can.height) * rect.height;
                var ev = new MouseEvent('$eventType', {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: clientX,
                    clientY: clientY,
                    button: $button,
                    buttons: $buttons
                });
                can.dispatchEvent(ev);
                if ('$eventType' === 'mouseup') {
                    var clickEv = new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: clientX,
                        clientY: clientY,
                        button: $button
                    });
                    can.dispatchEvent(clickEv);
                }
            })();
        """.trimIndent()
        wv.post { wv.evaluateJavascript(js, null) }
    }

    /**
     * Handles Hardware Bluetooth Gamepads and Keyboards.
     * Returns true if the key event was consumed for the game.
     */
    fun handleKeyEvent(event: KeyEvent): Boolean {
        if (targetWebView == null) return false

        val isDown = event.action == KeyEvent.ACTION_DOWN
        val androidKey = event.keyCode

        // Prevent repeat spam from flooding if state didn't change (except for movement)
        if (event.repeatCount > 0 && isDown) {
            // allow repeats for arrows
        }

        // Map Gamepad Buttons & Keyboard Keys to DOS equivalents
        val mapping: Triple<Int, String, String>? = when (androidKey) {
            // D-Pad / Arrow keys (Gamepad D-Pad & Keyboard Arrows)
            KeyEvent.KEYCODE_DPAD_UP -> Triple(38, "ArrowUp", "ArrowUp")
            KeyEvent.KEYCODE_DPAD_DOWN -> Triple(40, "ArrowDown", "ArrowDown")
            KeyEvent.KEYCODE_DPAD_LEFT -> Triple(37, "ArrowLeft", "ArrowLeft")
            KeyEvent.KEYCODE_DPAD_RIGHT -> Triple(39, "ArrowRight", "ArrowRight")

            // Gamepad Action Buttons (A/B/X/Y)
            // A -> Ctrl (Jump / Attack / Fire in most classic DOS games)
            KeyEvent.KEYCODE_BUTTON_A -> Triple(17, "Control", "ControlLeft")
            // B -> Alt (Strafe / Action / Sub-weapon)
            KeyEvent.KEYCODE_BUTTON_B -> Triple(18, "Alt", "AltLeft")
            // X -> Space (Open Doors / Action / Jump)
            KeyEvent.KEYCODE_BUTTON_X -> Triple(32, " ", "Space")
            // Y -> Shift (Run / Slow Walk)
            KeyEvent.KEYCODE_BUTTON_Y -> Triple(16, "Shift", "ShiftLeft")

            // Shoulder Buttons
            KeyEvent.KEYCODE_BUTTON_L1 -> Triple(32, " ", "Space")
            KeyEvent.KEYCODE_BUTTON_R1 -> Triple(17, "Control", "ControlLeft")

            // Start & Select
            KeyEvent.KEYCODE_BUTTON_START -> Triple(13, "Enter", "Enter")
            KeyEvent.KEYCODE_BUTTON_SELECT -> Triple(27, "Escape", "Escape")

            // Keyboard Standard Navigation & Modifiers
            KeyEvent.KEYCODE_ENTER -> Triple(13, "Enter", "Enter")
            KeyEvent.KEYCODE_ESCAPE -> Triple(27, "Escape", "Escape")
            KeyEvent.KEYCODE_SPACE -> Triple(32, " ", "Space")
            KeyEvent.KEYCODE_TAB -> Triple(9, "Tab", "Tab")
            KeyEvent.KEYCODE_DEL -> Triple(8, "Backspace", "Backspace")
            KeyEvent.KEYCODE_CTRL_LEFT, KeyEvent.KEYCODE_CTRL_RIGHT -> Triple(17, "Control", "ControlLeft")
            KeyEvent.KEYCODE_ALT_LEFT, KeyEvent.KEYCODE_ALT_RIGHT -> Triple(18, "Alt", "AltLeft")
            KeyEvent.KEYCODE_SHIFT_LEFT, KeyEvent.KEYCODE_SHIFT_RIGHT -> Triple(16, "Shift", "ShiftLeft")

            // Alphanumeric keys (A-Z, 0-9)
            in KeyEvent.KEYCODE_A..KeyEvent.KEYCODE_Z -> {
                val char = ('A' + (androidKey - KeyEvent.KEYCODE_A))
                Triple(char.code, char.toString(), "Key$char")
            }
            in KeyEvent.KEYCODE_0..KeyEvent.KEYCODE_9 -> {
                val digit = ('0' + (androidKey - KeyEvent.KEYCODE_0))
                Triple(digit.code, digit.toString(), "Digit$digit")
            }

            // Function keys (F1-F10)
            in KeyEvent.KEYCODE_F1..KeyEvent.KEYCODE_F12 -> {
                val num = (androidKey - KeyEvent.KEYCODE_F1) + 1
                Triple(111 + num, "F$num", "F$num")
            }

            else -> null
        }

        if (mapping != null) {
            val (jsKeyCode, key, code) = mapping
            sendJsKeyEvent(jsKeyCode, key, code, isDown)
            return true
        }

        return false
    }

    /**
     * Handles Analog Joystick motion (Left Stick) from Bluetooth Controllers.
     */
    fun handleMotionEvent(event: MotionEvent): Boolean {
        if (targetWebView == null) return false

        val x = event.getAxisValue(MotionEvent.AXIS_X)
        val y = event.getAxisValue(MotionEvent.AXIS_Y)
        val dpadX = event.getAxisValue(MotionEvent.AXIS_HAT_X)
        val dpadY = event.getAxisValue(MotionEvent.AXIS_HAT_Y)

        val effX = if (Math.abs(x) > 0.2f) x else dpadX
        val effY = if (Math.abs(y) > 0.2f) y else dpadY

        // Handle Horizontal
        val newLeft = effX < -0.5f
        val newRight = effX > 0.5f

        if (newLeft != stickLeft) {
            stickLeft = newLeft
            sendJsKeyEvent(37, "ArrowLeft", "ArrowLeft", stickLeft)
        }
        if (newRight != stickRight) {
            stickRight = newRight
            sendJsKeyEvent(39, "ArrowRight", "ArrowRight", stickRight)
        }

        // Handle Vertical
        val newUp = effY < -0.5f
        val newDown = effY > 0.5f

        if (newUp != stickUp) {
            stickUp = newUp
            sendJsKeyEvent(38, "ArrowUp", "ArrowUp", stickUp)
        }
        if (newDown != stickDown) {
            stickDown = newDown
            sendJsKeyEvent(40, "ArrowDown", "ArrowDown", stickDown)
        }

        return stickLeft || stickRight || stickUp || stickDown
    }
}

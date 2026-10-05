package org.archivevault.mobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Mouse
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.TouchApp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.archivevault.mobile.input.GameInputHandler
import org.archivevault.mobile.ui.theme.VaultPrimary
import org.archivevault.mobile.ui.theme.VaultSecondary

@Composable
fun VirtualGamepadDock(
    inputHandler: GameInputHandler?,
    modifier: Modifier = Modifier
) {
    var isMouseMode by remember { mutableStateOf(false) }

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .height(210.dp),
        color = Color(0xFF0C0F17),
        tonalElevation = 6.dp,
        shadowElevation = 10.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 14.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Left Control: D-Pad OR Thumb Trackpad
            if (isMouseMode) {
                ThumbTrackpadControl(
                    onMove = { dx, dy -> inputHandler?.sendJsMouseRelative(dx, dy) },
                    onTap = {
                        inputHandler?.sendJsMouseButton(0, true)
                        inputHandler?.sendJsMouseButton(0, false)
                    }
                )
            } else {
                DPadControl(
                    onDirectionPress = { keyCode, key, code, isDown ->
                        inputHandler?.sendJsKeyEvent(keyCode, key, code, isDown)
                    }
                )
            }

            // Center Column: ESC, Mode Toggle (Gamepad/Mouse), ENTER
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                ActionButton(
                    label = "ESC",
                    width = 54,
                    height = 34,
                    bgColor = Color(0xFF27272A),
                    textColor = Color(0xFFF43F5E),
                    onPressChange = { isDown ->
                        inputHandler?.sendJsKeyEvent(27, "Escape", "Escape", isDown)
                    }
                )

                // Mode Switcher: PAD vs MOUSE
                Surface(
                    onClick = { isMouseMode = !isMouseMode },
                    color = if (isMouseMode) VaultSecondary else VaultPrimary,
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.size(width = 54.dp, height = 34.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = if (isMouseMode) Icons.Default.Mouse else Icons.Default.SportsEsports,
                            contentDescription = "Switch Input Mode",
                            tint = Color.Black,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }

                ActionButton(
                    label = "ENTER",
                    width = 54,
                    height = 34,
                    bgColor = Color(0xFF27272A),
                    textColor = VaultPrimary,
                    onPressChange = { isDown ->
                        inputHandler?.sendJsKeyEvent(13, "Enter", "Enter", isDown)
                    }
                )
            }

            // Right Control: Action Buttons OR Mouse Buttons
            if (isMouseMode) {
                MouseButtonsControl(
                    onMouseButton = { button, isDown ->
                        inputHandler?.sendJsMouseButton(button, isDown)
                    }
                )
            } else {
                ActionButtonsControl(
                    onActionPress = { keyCode, key, code, isDown ->
                        inputHandler?.sendJsKeyEvent(keyCode, key, code, isDown)
                    }
                )
            }
        }
    }
}

@Composable
fun ThumbTrackpadControl(
    modifier: Modifier = Modifier,
    onMove: (dx: Float, dy: Float) -> Unit,
    onTap: () -> Unit
) {
    Box(
        modifier = modifier
            .size(145.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFF141926))
            .border(1.dp, VaultPrimary.copy(alpha = 0.5f), RoundedCornerShape(16.dp))
            .pointerInput(Unit) {
                detectTapGestures(onTap = { onTap() })
            }
            .pointerInput(Unit) {
                detectDragGestures { change, dragAmount ->
                    change.consume()
                    onMove(dragAmount.x * 2.2f, dragAmount.y * 2.2f)
                }
            },
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(
                imageVector = Icons.Default.TouchApp,
                contentDescription = null,
                tint = VaultPrimary,
                modifier = Modifier.size(28.dp)
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text("Thumb Trackpad", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            Text("Drag to aim • Tap to click", color = Color.Gray, fontSize = 8.sp)
        }
    }
}

@Composable
fun MouseButtonsControl(
    modifier: Modifier = Modifier,
    onMouseButton: (button: Int, isDown: Boolean) -> Unit
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(10.dp),
        horizontalAlignment = Alignment.End
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            ActionButton(
                label = "L-CLICK",
                width = 66,
                height = 46,
                bgColor = Color(0xFF1E3A8A),
                textColor = VaultPrimary,
                onPressChange = { onMouseButton(0, it) }
            )
            ActionButton(
                label = "R-CLICK",
                width = 66,
                height = 46,
                bgColor = Color(0xFF064E3B),
                textColor = VaultSecondary,
                onPressChange = { onMouseButton(2, it) }
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            ActionButton(
                label = "DOUBLE CLICK ⚡",
                width = 142,
                height = 46,
                bgColor = Color(0xFF2E1065),
                textColor = Color(0xFFC084FC),
                onPressChange = { isDown ->
                    if (isDown) {
                        onMouseButton(0, true)
                        onMouseButton(0, false)
                        onMouseButton(0, true)
                        onMouseButton(0, false)
                    }
                }
            )
        }
    }
}

@Composable
fun DPadControl(
    modifier: Modifier = Modifier,
    onDirectionPress: (keyCode: Int, key: String, code: String, isDown: Boolean) -> Unit
) {
    Box(
        modifier = modifier
            .size(145.dp)
            .background(Color(0xFF141926), CircleShape)
            .padding(6.dp),
        contentAlignment = Alignment.Center
    ) {
        // Up
        DPadButton(
            icon = Icons.Default.KeyboardArrowUp,
            modifier = Modifier.align(Alignment.TopCenter),
            onPressChange = { isDown -> onDirectionPress(38, "ArrowUp", "ArrowUp", isDown) }
        )
        // Down
        DPadButton(
            icon = Icons.Default.KeyboardArrowDown,
            modifier = Modifier.align(Alignment.BottomCenter),
            onPressChange = { isDown -> onDirectionPress(40, "ArrowDown", "ArrowDown", isDown) }
        )
        // Left
        DPadButton(
            icon = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
            modifier = Modifier.align(Alignment.CenterStart),
            onPressChange = { isDown -> onDirectionPress(37, "ArrowLeft", "ArrowLeft", isDown) }
        )
        // Right
        DPadButton(
            icon = Icons.AutoMirrored.Filled.KeyboardArrowRight,
            modifier = Modifier.align(Alignment.CenterEnd),
            onPressChange = { isDown -> onDirectionPress(39, "ArrowRight", "ArrowRight", isDown) }
        )
    }
}

@Composable
fun DPadButton(
    icon: ImageVector,
    modifier: Modifier = Modifier,
    onPressChange: (isDown: Boolean) -> Unit
) {
    Box(
        modifier = modifier
            .size(44.dp)
            .clip(RoundedCornerShape(8.dp))
            .background(Color(0xFF232D42))
            .pointerInput(Unit) {
                detectTapGestures(
                    onPress = {
                        onPressChange(true)
                        tryAwaitRelease()
                        onPressChange(false)
                    }
                )
            },
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = VaultPrimary,
            modifier = Modifier.size(28.dp)
        )
    }
}

@Composable
fun ActionButtonsControl(
    modifier: Modifier = Modifier,
    onActionPress: (keyCode: Int, key: String, code: String, isDown: Boolean) -> Unit
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(10.dp),
        horizontalAlignment = Alignment.End
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            ActionButton(
                label = "CTRL",
                width = 58,
                height = 46,
                bgColor = Color(0xFF1E3A8A),
                textColor = VaultPrimary,
                onPressChange = { onActionPress(17, "Control", "ControlLeft", it) }
            )
            ActionButton(
                label = "ALT",
                width = 58,
                height = 46,
                bgColor = Color(0xFF064E3B),
                textColor = VaultSecondary,
                onPressChange = { onActionPress(18, "Alt", "AltLeft", it) }
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            ActionButton(
                label = "SPACE",
                width = 126,
                height = 46,
                bgColor = Color(0xFF2E1065),
                textColor = Color(0xFFC084FC),
                onPressChange = { onActionPress(32, " ", "Space", it) }
            )
        }
    }
}

@Composable
fun ActionButton(
    label: String,
    width: Int = 54,
    height: Int = 46,
    bgColor: Color = Color(0xFF1E3A8A),
    textColor: Color = Color.White,
    onPressChange: (isDown: Boolean) -> Unit
) {
    Box(
        modifier = Modifier
            .size(width = width.dp, height = height.dp)
            .clip(RoundedCornerShape(10.dp))
            .background(bgColor)
            .pointerInput(Unit) {
                detectTapGestures(
                    onPress = {
                        onPressChange(true)
                        tryAwaitRelease()
                        onPressChange(false)
                    }
                )
            },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            color = textColor,
            fontSize = 12.sp,
            fontWeight = FontWeight.ExtraBold
        )
    }
}

package org.archivevault.mobile.player

import android.content.Context
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class AudioTrackState(
    val title: String = "",
    val url: String = "",
    val isPlaying: Boolean = false,
    val durationMs: Long = 0L,
    val positionMs: Long = 0L,
    val isVisible: Boolean = false
)

class AudioPlayerController private constructor(context: Context) {

    private val player = ExoPlayer.Builder(context).build().apply {
        repeatMode = Player.REPEAT_MODE_OFF
        addListener(object : Player.Listener {
            override fun onIsPlayingChanged(isPlaying: Boolean) {
                _trackState.value = _trackState.value.copy(
                    isPlaying = isPlaying,
                    durationMs = duration.coerceAtLeast(0L),
                    positionMs = currentPosition.coerceAtLeast(0L)
                )
            }

            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED) {
                    _trackState.value = _trackState.value.copy(isPlaying = false)
                }
            }
        })
    }

    private val _trackState = MutableStateFlow(AudioTrackState())
    val trackState: StateFlow<AudioTrackState> = _trackState.asStateFlow()

    fun play(url: String, title: String) {
        val mediaItem = MediaItem.fromUri(url)
        player.setMediaItem(mediaItem)
        player.prepare()
        player.play()
        _trackState.value = AudioTrackState(
            title = title,
            url = url,
            isPlaying = true,
            isVisible = true
        )
    }

    fun togglePlayPause() {
        if (player.isPlaying) {
            player.pause()
        } else {
            player.play()
        }
    }

    fun seekTo(positionMs: Long) {
        player.seekTo(positionMs)
    }

    fun stop() {
        player.stop()
        _trackState.value = _trackState.value.copy(isPlaying = false, isVisible = false)
    }

    companion object {
        @Volatile
        private var instance: AudioPlayerController? = null

        fun getInstance(context: Context): AudioPlayerController {
            return instance ?: synchronized(this) {
                instance ?: AudioPlayerController(context.applicationContext).also { instance = it }
            }
        }
    }
}

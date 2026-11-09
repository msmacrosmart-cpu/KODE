package com.smarted.tv.ui.player

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.KeyEvent
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView

/**
 * Player de vídeo (Media3/ExoPlayer) usado por Canais, Filmes e Séries.
 * Aceita HLS (.m3u8), MP4 e progressive via URL.
 */
class PlayerActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        val streamUrl = intent.getStringExtra(EXTRA_STREAM_URL).orEmpty()
        val title = intent.getStringExtra(EXTRA_TITLE) ?: "Reprodução"
        val mimeHint = intent.getStringExtra(EXTRA_MIME)

        setContent {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black),
            ) {
                if (streamUrl.isBlank()) {
                    Text(
                        text = "URL de stream inválida",
                        color = Color.White,
                        modifier = Modifier.align(Alignment.Center),
                    )
                } else {
                    VideoPlayer(url = streamUrl, mimeHint = mimeHint)
                    Text(
                        text = title,
                        color = Color.White,
                        modifier = Modifier.align(Alignment.TopStart),
                    )
                }
            }
        }
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        when (keyCode) {
            KeyEvent.KEYCODE_BACK, KeyEvent.KEYCODE_ESCAPE -> {
                finish()
                return true
            }
        }
        return super.onKeyDown(keyCode, event)
    }

    companion object {
        private const val EXTRA_STREAM_URL = "stream_url"
        private const val EXTRA_TITLE = "title"
        private const val EXTRA_MIME = "mime"

        /**
         * @param mimeHint MIME explícito (HLS/DASH). Necessário para streams sem
         * extensão; sem ele o Media3 tenta inferir pela URI.
         */
        fun intent(context: Context, streamUrl: String, title: String, mimeHint: String? = null): Intent =
            Intent(context, PlayerActivity::class.java)
                .putExtra(EXTRA_STREAM_URL, streamUrl)
                .putExtra(EXTRA_TITLE, title)
                .putExtra(EXTRA_MIME, mimeHint)
    }
}

@Composable
private fun VideoPlayer(url: String, mimeHint: String?) {
    val context = LocalContext.current
    var isPlaying by remember { mutableStateOf(true) }

    val player = remember {
        ExoPlayer.Builder(context).build().apply {
            // `content://` (SAF) e `file://` tocam direto; HLS/DASH precisam do MIME
            // quando a URI não tem extensão (a URL original é preservada inteira,
            // com query string — nada é truncado).
            val item = MediaItem.Builder().setUri(url)
            val mime = mimeHint ?: mimeFromUri(url)
            if (mime != null) item.setMimeType(mime)
            setMediaItem(item.build())
            prepare()
            playWhenReady = true
        }
    }

    DisposableEffect(player) {
        val listener = object : Player.Listener {
            override fun onIsPlayingChanged(playing: Boolean) {
                isPlaying = playing
            }
        }
        player.addListener(listener)
        onDispose {
            player.removeListener(listener)
            player.release()
        }
    }

    AndroidView(
        factory = { ctx ->
            PlayerView(ctx).apply {
                this.player = player
                useController = true
                setShowBuffering(PlayerView.SHOW_BUFFERING_ALWAYS)
            }
        },
        modifier = Modifier.fillMaxSize(),
    )
}

/** MIME pela extensão, só quando conhecido (nunca adivinha). */
private fun mimeFromUri(uri: String): String? {
    val path = uri.substringBefore('?').substringBefore('#').lowercase()
    return when {
        path.endsWith(".m3u8") -> MimeTypes.APPLICATION_M3U8
        path.endsWith(".mpd") -> MimeTypes.APPLICATION_MPD
        path.endsWith(".mp4") || path.endsWith(".m4v") -> MimeTypes.VIDEO_MP4
        path.endsWith(".webm") -> MimeTypes.VIDEO_WEBM
        path.endsWith(".mkv") -> "video/x-matroska"
        path.endsWith(".ts") -> MimeTypes.VIDEO_MP2T
        path.endsWith(".flac") -> "audio/flac"
        path.endsWith(".mp3") -> MimeTypes.AUDIO_MPEG
        path.endsWith(".m4a") || path.endsWith(".aac") -> MimeTypes.AUDIO_AAC
        path.endsWith(".ogg") || path.endsWith(".opus") -> MimeTypes.AUDIO_OGG
        else -> null
    }
}

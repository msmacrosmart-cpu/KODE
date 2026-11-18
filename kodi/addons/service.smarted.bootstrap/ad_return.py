"""One in-memory playback hand-off per pre-roll. Disk carries a nonce, never a media URL or VIP data."""
import json
import os
import threading
import time
import uuid

import xbmc
import xbmcvfs


def rpc(method, **params):
    reply = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1,
                                                       'method': method, 'params': params})))
    if 'error' in reply:
        raise RuntimeError(method + ' recusado')
    return reply['result']


class KodiVideo:
    def __init__(self, player):
        self.player = player
        self.pid = next(p['playerid'] for p in rpc('Player.GetActivePlayers') if p['type'] == 'video')
        props = rpc('Player.GetProperties', playerid=self.pid,
                    properties=['speed', 'canpause', 'canseek', 'live'])
        self.was_playing = props['speed'] != 0
        self.can_pause, self.can_seek = props['canpause'], props['canseek']
        self.path = player.getPlayingFile()
        self.channel = xbmc.getInfoLabel('VideoPlayer.ChannelName') or ''
        self.live = props['live'] or bool(self.channel) or self.path.startswith('pvr://')
        self.channel_id = None
        self.item = None
        if self.live and not self.can_pause:
            item = rpc('Player.GetItem', playerid=self.pid).get('item', {})
            if item.get('type') == 'channel':
                self.channel_id = item.get('id')
            try:
                self.item = player.getPlayingItem()
            except (AttributeError, RuntimeError):
                pass
        self.position = None

    def same(self):
        if not self.player.isPlayingVideo():
            return False
        path = self.player.getPlayingFile()
        now = xbmc.getInfoLabel('VideoPlayer.ChannelName') or ''
        return path == self.path and not (self.channel and now and self.channel != now)

    def hold(self):
        if self.can_pause and self.was_playing:
            rpc('Player.PlayPause', playerid=self.pid, play=False)  # never toggle
        if self.can_seek and self.was_playing:
            self.position = self.player.getTime()

    def release(self):
        if self.same() and self.was_playing:
            if self.position is not None and abs(self.player.getTime() - self.position) > 0.25:
                self.player.seekTime(self.position)
            if self.can_pause:
                rpc('Player.PlayPause', playerid=self.pid, play=True)

    def reopen_live(self):
        # Never seek a live edge to a movie timestamp. Preserve the resolved ListItem if available.
        if self.channel_id is not None:
            rpc('Player.Open', item={'channelid': self.channel_id})
        elif self.path and self.item is not None:
            self.player.play(self.path, self.item)
        elif self.path:
            self.player.play(self.path)


class Breaks:
    def __init__(self, log=None):
        self.log = log or (lambda *args: None)
        self.lock = threading.RLock()
        self.current = self.replay = None

    @staticmethod
    def remove(stem):
        for ext in ('.pending', '.open', '.returned'):
            try:
                os.unlink(stem + ext)
            except OSError:
                pass

    def cancel(self):
        with self.lock:
            if self.current:
                self.remove(self.current['stem'])
            self.current = None

    def stopped(self, ended=False):
        with self.lock:
            state = self.current
            if not ended and state and os.path.isfile(state['stem'] + '.open'):
                video = state['video']
                if video.live and not video.can_pause and video.was_playing:
                    state['stopped_live'] = True
                    return
            self.cancel()
            self.replay = None

    def is_replay(self, path, channel):
        with self.lock:
            last, self.replay = self.replay, None
            return bool(last and time.monotonic() <= last[2] and
                        ((channel and channel == last[1]) or (path and path == last[0] and
                         not (channel and last[1] and channel != last[1]))))

    def start(self, video, launch):
        with self.lock:
            self.cancel()
            folder = os.path.join(xbmcvfs.translatePath('special://home'), 'temp', 'smarted-ad')
            os.makedirs(folder, exist_ok=True)
            token = uuid.uuid4().hex
            stem = os.path.join(folder, token)
            with open(stem + '.pending', 'xb'):
                pass
            state = {'video': video, 'stem': stem, 'stopped_live': False}
            self.current = state
            try:
                video.hold()
                if not launch(token):
                    self.finish(state)
                    return False
                worker = threading.Thread(target=self.wait, args=(state,), name='retorno-anuncio')
                worker.daemon = True
                worker.start()
                return True
            except Exception:
                self.finish(state)
                raise

    def wait(self, state):
        mon = xbmc.Monitor()
        until = time.monotonic() + 6
        try:
            while not mon.waitForAbort(0.15):
                with self.lock:
                    if self.current is not state:
                        return
                    stem = state['stem']
                    if os.path.isfile(stem + '.returned'):
                        self.finish(state)
                        return
                    # Only expire an intent which Android NEVER opened. A shown ad or an
                    # external browser doesn't get a guessed time limit from Python.
                    if time.monotonic() > until and os.path.isfile(stem + '.pending'):
                        try:
                            os.unlink(stem + '.pending')  # wins OR loses against Java's rename
                        except FileNotFoundError:
                            continue
                        self.log('[SmartAds] activity não confirmou a abertura; liberando vídeo')
                        self.finish(state)
                        return
        except Exception as exc:
            self.log('[SmartAds] retorno: %s' % type(exc).__name__)
        finally:
            with self.lock:
                if self.current is state:
                    self.cancel()  # abort/quit: never resurrect a player

    def finish(self, state):
        with self.lock:
            if self.current is not state:
                return
            video = state['video']
            self.cancel()
            if state['stopped_live'] and not video.player.isPlaying():
                self.replay = (video.path, video.channel, time.monotonic() + 15)
                video.reopen_live()
            else:
                video.release()
            self.log('[SmartAds] retorno ao player processado')

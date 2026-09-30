extends Node
## Sfx: plays generated wav files. Music loops seamlessly (they are looped at
## authoring time). A small pool of players lets effects overlap.

var _pool: Array[AudioStreamPlayer] = []
var _music: AudioStreamPlayer = null
var _cache: Dictionary = {}

func _ready() -> void:
	for i in 8:
		var p := AudioStreamPlayer.new()
		p.bus = "Master"
		add_child(p)
		_pool.append(p)
	_music = AudioStreamPlayer.new()
	_music.bus = "Master"
	add_child(_music)

func _stream(path: String) -> AudioStream:
	if _cache.has(path):
		return _cache[path]
	var s: AudioStream = load(path)
	_cache[path] = s
	return s

func play(name: String, pitch: float = 1.0, volume: float = 1.0) -> void:
	var path := "res://assets/sfx/%s.wav" % name
	var s := _stream(path)
	if s == null:
		return
	for p in _pool:
		if not p.playing:
			p.stream = s
			p.pitch_scale = pitch
			p.volume_db = linear_to_db(volume)
			p.play()
			return
	# all busy: reuse the first
	var p := _pool[0]
	p.stream = s
	p.pitch_scale = pitch
	p.play()

func play_music(name: String) -> void:
	var path := "res://assets/music/%s.wav" % name
	var s := _stream(path)
	if s == null:
		return
	if s is AudioStreamWAV:
		(s as AudioStreamWAV).loop_mode = AudioStreamWAV.LOOP_FORWARD
	_music.stream = s
	_music.volume_db = linear_to_db(0.8)
	_music.play()

func stop_music() -> void:
	_music.stop()

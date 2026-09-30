extends CanvasLayer
## Weather particles + storm flashes. Attached above world, below UI.

var _rain: GPUParticles2D = null
var _snow: GPUParticles2D = null
var _flash: ColorRect = null
var _thunder_t := 0.0

func _ready() -> void:
	layer = 5
	Game.day_changed.connect(func(_d, s, _y): _apply())
	_apply()

func _apply() -> void:
	for ch in get_children():
		ch.queue_free()
	_flash = null
	var w := Game.weather
	if w == "rain" or w == "storm":
		_rain = _make_particles("raindrop", 260 if w == "rain" else 420, 0.7, Vector2(0, 900), Vector2(-60, 0))
		add_child(_rain)
	if w == "snow" or (Game.season == 3 and w != "storm"):
		_snow = _make_particles("snowflake", 160, 4.0, Vector2(0, 140), Vector2(30, 0))
		add_child(_snow)
	if w == "storm":
		_flash = ColorRect.new()
		_flash.color = Color(1, 1, 1, 0)
		_flash.set_anchors_preset(Control.PRESET_FULL_RECT)
		add_child(_flash)

func _make_particles(tex: String, amount: int, life: float, grav: Vector2, init_v: Vector2) -> GPUParticles2D:
	var p := GPUParticles2D.new()
	p.amount = amount
	p.lifetime = life
	p.texture = Art.tex(tex)
	p.emitting = true
	var m := ParticleProcessMaterial.new()
	m.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	m.emission_box_extents = Vector3(760, 10, 1)
	m.direction = Vector3(0, 1, 0)
	m.initial_velocity_min = init_v.length()
	m.initial_velocity_max = init_v.length() * 1.2
	m.gravity = grav
	m.spread = 6.0
	p.process_material = m
	p.position = Vector2(640, -20)
	return p

func _process(delta: float) -> void:
	if _flash and Game.weather == "storm":
		_thunder_t -= delta
		if _thunder_t <= 0:
			_thunder_t = randf_range(4.0, 9.0)
			Sfx.play("thunder", 0.9, 0.6)
			_flash.color = Color(1, 1, 1, 0.5)
			get_tree().create_timer(0.1).timeout.connect(func(): _flash.color = Color(1, 1, 1, 0.15))
			get_tree().create_timer(0.25).timeout.connect(func(): _flash.color = Color(1, 1, 1, 0.0))

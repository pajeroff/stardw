extends CanvasLayer
## The bar-and-fish catch minigame (Stardew-style). Fully code-built UI.

signal finished(success: bool, treasure: bool)

const TRACK_H := 300.0
const TRACK_W := 46.0

var difficulty := 2.0
var luck := 0.0
var treasure_chance := 0.12

var _track: ColorRect = null
var _bar: ColorRect = null
var _fish: TextureRect = null
var _treasure: TextureRect = null
var _prog_bg: ColorRect = null
var _prog: ColorRect = null
var _panel: PanelContainer = null

var bar_y := 0.0
var bar_vel := 0.0
var bar_h := 80.0
var fish_y := 0.0
var fish_vel := 0.0
var fish_target := 0.0
var fish_timer := 0.0
var progress := 0.35
var treasure_y := -1.0
var got_treasure := false
var running := false
var _t := 0.0

func start(diff: float, bar_mult: float, grip: float, tres_mult: float) -> void:
	difficulty = diff
	bar_h = clampf(80.0 * bar_mult, 40.0, 140.0)
	treasure_chance = 0.12 * tres_mult
	_build_ui()
	running = true

func _build_ui() -> void:
	_panel = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.08, 0.12, 0.18, 0.92)
	sb.border_color = Color(0.3, 0.5, 0.7)
	sb.set_border_width_all(3)
	sb.set_corner_radius_all(8)
	_panel.add_theme_stylebox_override("panel", sb)
	add_child(_panel)
	_panel.set_anchors_preset(Control.PRESET_CENTER)
	_panel.position = Vector2(-60, -TRACK_H * 0.5 - 20)
	_panel.size = Vector2(120, TRACK_H + 40)

	_track = ColorRect.new()
	_track.color = Color(0.05, 0.15, 0.25)
	_track.size = Vector2(TRACK_W, TRACK_H)
	_track.position = Vector2(12, 20)
	_panel.add_child(_track)

	_bar = ColorRect.new()
	_bar.color = Color(0.35, 0.85, 0.45)
	_bar.size = Vector2(TRACK_W, bar_h)
	_panel.add_child(_bar)

	_fish = TextureRect.new()
	_fish.texture = Art.tex("fish_marker")
	_fish.size = Vector2(24, 24)
	_panel.add_child(_fish)

	_treasure = TextureRect.new()
	_treasure.texture = Art.tex("treasure_marker")
	_treasure.size = Vector2(20, 20)
	_treasure.visible = false
	_panel.add_child(_treasure)

	_prog_bg = ColorRect.new()
	_prog_bg.color = Color(0.1, 0.1, 0.12)
	_prog_bg.size = Vector2(12, TRACK_H)
	_prog_bg.position = Vector2(TRACK_W + 26, 20)
	_panel.add_child(_prog_bg)

	_prog = ColorRect.new()
	_prog.color = Color(0.95, 0.8, 0.35)
	_prog.size = Vector2(12, TRACK_H * progress)
	_panel.add_child(_prog)

	bar_y = (TRACK_H - bar_h) * 0.5
	fish_y = TRACK_H * 0.5
	fish_target = fish_y

func _holding() -> bool:
	return Input.is_action_pressed("use") or Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)

func _process(delta: float) -> void:
	if not running:
		return
	_t += delta
	# --- player bar physics ---
	if _holding():
		bar_vel -= 1400.0 * delta
	else:
		bar_vel += 1200.0 * delta
	bar_vel = clampf(bar_vel, -520.0, 520.0)
	bar_y += bar_vel * delta
	if bar_y < 0:
		bar_y = 0
		bar_vel = 0
	if bar_y > TRACK_H - bar_h:
		bar_y = TRACK_H - bar_h
		bar_vel = 0
	_bar.position = Vector2(12, 20 + bar_y)

	# --- fish AI ---
	fish_timer -= delta
	if fish_timer <= 0:
		fish_timer = randf_range(0.5, 1.4) - difficulty * 0.06
		fish_target = randf_range(10.0, TRACK_H - 10.0)
	var spd := (60.0 + difficulty * 46.0)
	var d := fish_target - fish_y
	fish_y += clampf(d, -spd * delta, spd * delta)
	fish_y = clampf(fish_y, 8.0, TRACK_H - 8.0)
	_fish.position = Vector2(12 + TRACK_W * 0.5 - 12, 20 + fish_y - 12)

	# --- treasure ---
	if treasure_y < 0 and randf() < treasure_chance * delta:
		treasure_y = randf_range(20.0, TRACK_H - 20.0)
		_treasure.visible = true
	if treasure_y >= 0:
		_treasure.position = Vector2(12 + TRACK_W * 0.5 - 10, 20 + treasure_y - 10)
		if fish_y >= 0 and absf((bar_y + bar_h * 0.5) - treasure_y) < bar_h * 0.5:
			if not got_treasure:
				got_treasure = true
				Sfx.play("coin")
			_treasure.visible = false
			treasure_y = -1.0

	# --- progress ---
	var overlap := fish_y >= bar_y and fish_y <= bar_y + bar_h
	if overlap:
		progress += (0.42 + luck * 0.01) * delta
	else:
		progress -= (0.30 + difficulty * 0.02) * delta
	progress = clampf(progress, 0.0, 1.0)
	_prog.size.y = TRACK_H * progress
	_prog.position = Vector2(TRACK_W + 26, 20 + TRACK_H * (1.0 - progress))
	_bar.color = Color(0.35, 0.85, 0.45) if overlap else Color(0.4, 0.5, 0.5)

	if progress >= 1.0:
		_end(true)
	elif progress <= 0.0:
		_end(false)

func _end(success: bool) -> void:
	running = false
	_panel.queue_free()
	finished.emit(success, got_treasure)

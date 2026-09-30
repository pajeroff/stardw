extends CanvasLayer
## HUD: top status bar, bottom hotbar, toasts and interaction prompt.

const U = preload("res://scripts/ui/ui_util.gd")

var player = null
var world = null

var _season_icon: TextureRect = null
var _date_lbl: Label = null
var _weather_icon: TextureRect = null
var _clock_lbl: Label = null
var _gold_lbl: Label = null
var _energy_fill: ColorRect = null
var _energy_bg: ColorRect = null
var _prompt: Label = null
var _toasts: Array = []
var _slots: Array = []          # PanelContainer per slot
var _slot_icons: Array = []
var _slot_counts: Array = []
var selected := 0

func _ready() -> void:
	layer = 10
	_build_top()
	_build_hotbar()
	_build_prompt()
	Game.gold_changed.connect(func(v): _gold_lbl.text = str(v))
	Game.energy_changed.connect(func(_v): _update_energy())
	Game.day_changed.connect(func(_d, s, _y): _update_date(s))
	Game.clock_changed.connect(func(h, m): _clock_lbl.text = "%02d:%02d" % [h, m])
	Game.inventory_changed.connect(_refresh_hotbar)
	Game.toast.connect(_add_toast)
	_gold_lbl.text = str(Game.gold)
	_update_date(Game.season)
	_update_energy()
	_refresh_hotbar()

func _build_top() -> void:
	var top := Control.new()
	top.set_anchors_preset(Control.PRESET_TOP_WIDE)
	top.custom_minimum_size = Vector2(0, 56)
	add_child(top)
	var bar := ColorRect.new()
	bar.color = Color(0.05, 0.08, 0.12, 0.85)
	bar.set_anchors_preset(Control.PRESET_TOP_WIDE)
	bar.size = Vector2(1280, 52)
	top.add_child(bar)

	var hbox := HBoxContainer.new()
	hbox.position = Vector2(14, 8)
	top.add_child(hbox)

	_season_icon = TextureRect.new()
	_season_icon.custom_minimum_size = Vector2(28, 28)
	hbox.add_child(_season_icon)
	_date_lbl = U.label("", 18)
	hbox.add_child(_date_lbl)
	_weather_icon = TextureRect.new()
	_weather_icon.custom_minimum_size = Vector2(28, 28)
	hbox.add_child(_weather_icon)
	_clock_lbl = U.label("", 18, Color(0.9, 0.9, 0.7))
	hbox.add_child(_clock_lbl)

	var right := HBoxContainer.new()
	right.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	right.position = Vector2(-320, 10)
	top.add_child(right)
	right.add_child(U.icon("ic_gold", 26))
	_gold_lbl = U.label("", 18, Color(1, 0.85, 0.4))
	right.add_child(_gold_lbl)
	var sep := Control.new()
	sep.custom_minimum_size = Vector2(20, 0)
	right.add_child(sep)
	right.add_child(U.icon("ic_energy", 26))
	_energy_bg = ColorRect.new()
	_energy_bg.color = Color(0.1, 0.1, 0.12)
	_energy_bg.custom_minimum_size = Vector2(140, 16)
	_energy_bg.size = Vector2(140, 16)
	right.add_child(_energy_bg)
	_energy_fill = ColorRect.new()
	_energy_fill.color = Color(0.45, 0.85, 0.4)
	_energy_fill.size = Vector2(140, 16)
	_energy_bg.add_child(_energy_fill)

func _update_energy() -> void:
	if _energy_fill:
		_energy_fill.size.x = 140.0 * Game.energy / float(Game.max_energy)
		_energy_fill.color = Color(0.45, 0.85, 0.4) if Game.energy > 30 else Color(0.9, 0.5, 0.3)

func _update_date(season: int) -> void:
	_season_icon.texture = Art.tex(["s_spring", "s_summer", "s_autumn", "s_winter"][season])
	_weather_icon.texture = Art.tex({"sun": "w_sun", "rain": "w_rain", "storm": "w_storm", "snow": "w_snow"}[Game.weather])
	_date_lbl.text = "%s %d, г.%d" % [DB.SEASONS[season], Game.day, Game.year]

func _build_hotbar() -> void:
	var hb := HBoxContainer.new()
	hb.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	hb.position = Vector2(-6 * 46, -56)
	hb.add_theme_constant_override("separation", 6)
	add_child(hb)
	for i in 12:
		var p := PanelContainer.new()
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0.08, 0.1, 0.14, 0.9)
		sb.border_color = Color(0.35, 0.4, 0.5)
		sb.set_border_width_all(2)
		sb.set_corner_radius_all(6)
		p.add_theme_stylebox_override("panel", sb)
		p.custom_minimum_size = Vector2(44, 44)
		hb.add_child(p)
		var box := VBoxContainer.new()
		p.add_child(box)
		var ic := TextureRect.new()
		ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		ic.custom_minimum_size = Vector2(30, 30)
		ic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		box.add_child(ic)
		var cnt := U.label("", 11, Color(0.9, 0.9, 0.9))
		cnt.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		box.add_child(cnt)
		_slots.append(p)
		_slot_icons.append(ic)
		_slot_counts.append(cnt)

func _refresh_hotbar() -> void:
	for i in 12:
		var ic: TextureRect = _slot_icons[i]
		var cnt: Label = _slot_counts[i]
		var sb: StyleBoxFlat = _slots[i].get_theme_stylebox("panel")
		if i < Game.inventory.size():
			var it = Game.inventory[i]
			ic.texture = _icon_for(it["id"])
			cnt.text = str(it["count"]) if it["count"] > 1 else ""
		else:
			ic.texture = null
			cnt.text = ""
		sb.border_color = Color(1, 0.85, 0.3) if i == selected else Color(0.35, 0.4, 0.5)
		sb.set_border_width_all(3 if i == selected else 2)

func _icon_for(id: String) -> Texture2D:
	if Art.has(id):
		return Art.tex(id)
	return Art.tex("ic_fish")

func _build_prompt() -> void:
	_prompt = U.label("", 16, Color(1, 0.9, 0.6))
	_prompt.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_prompt.position = Vector2(-150, -90)
	_prompt.visible = false
	add_child(_prompt)

func _process(_d: float) -> void:
	if player and world:
		var kind := world.interactable_near(player._cell())
		if kind != "":
			var names := {"shop": "Магазин", "house": "Дом (сон)", "board": "Доска заказов",
						  "well": "Колодец", "campfire": "Костёр", "boat": "Лодка"}
			_prompt.text = "[E] %s" % names.get(kind, kind)
			_prompt.visible = true
		else:
			_prompt.visible = false

func _unhandled_input(ev: InputEvent) -> void:
	if ev is InputEventKey and ev.pressed:
		var idx := -1
		match ev.keycode:
			KEY_1: idx = 0
			KEY_2: idx = 1
			KEY_3: idx = 2
			KEY_4: idx = 3
			KEY_5: idx = 4
			KEY_6: idx = 5
			KEY_7: idx = 6
			KEY_8: idx = 7
			KEY_9: idx = 8
			KEY_0: idx = 9
		if idx >= 0:
			_select(idx)

func _select(i: int) -> void:
	selected = i
	if i < Game.inventory.size():
		var it = Game.inventory[i]
		var typ: String = str(DB.item_by_id(it["id"]).get("type", ""))
		if typ == "food":
			if Game.remove_item(it["id"], 1):
				Game.restore_energy(DB.item_by_id(it["id"]).get("energy", 20))
				Sfx.play("ui")
				Game.emit_toast("+%d энергии: %s" % [DB.item_by_id(it["id"]).get("energy", 20), DB.item_by_id(it["id"])["name"]], Color(0.6, 0.9, 0.5))
			_refresh_hotbar()
			return
		elif typ == "rod":
			Game.rod_id = it["id"]
			Game.emit_toast("Удочка: %s" % DB.item_by_id(it["id"])["name"], Color(0.8, 0.8, 1))
		elif typ == "bait":
			Game.bait_id = it["id"]
		elif typ == "tackle":
			Game.tackle_id = it["id"]
		elif typ == "lure":
			Game.lure_id = it["id"]
		Sfx.play("ui")
	_refresh_hotbar()

func _add_toast(text: String, col: Color) -> void:
	var l := U.label(text, 17, col)
	l.set_anchors_preset(Control.PRESET_CENTER_TOP)
	l.position = Vector2(-300, 90 + _toasts.size() * 30)
	l.modulate.a = 1.0
	add_child(l)
	_toasts.append(l)
	get_tree().create_timer(3.0).timeout.connect(func():
		_toasts.erase(l)
		l.queue_free())

extends CanvasLayer
## Fish catalog (dex).

const U = preload("res://scripts/ui/ui_util.gd")

signal closed()
var _root: Control = null
var _open := false

func _ready() -> void:
	layer = 25

func is_open() -> bool:
	return _open

func open() -> void:
	if _open:
		return
	_open = true
	_build()

func close() -> void:
	_open = false
	if _root:
		_root.queue_free()
		_root = null
	closed.emit()

func _build() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.6)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(dim)

	var p := U.panel_container(14)
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.position = Vector2(-470, -270)
	p.size = Vector2(940, 540)
	_root.add_child(p)

	var vbox := VBoxContainer.new()
	p.add_child(vbox)
	var head := HBoxContainer.new()
	vbox.add_child(head)
	head.add_child(U.label("Каталог рыб", 22, Color(0.6, 0.9, 0.8)))
	var pct := U.label("  %d / %d" % [Game.dex.size(), DB.fish.size()], 18, Color(0.9, 0.9, 0.9))
	head.add_child(pct)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(spacer)
	var close_btn := U.button("Закрыть [F]")
	close_btn.pressed.connect(close)
	head.add_child(close_btn)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(scroll)
	var grid := GridContainer.new()
	grid.columns = 6
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 10)
	scroll.add_child(grid)

	for id in DB.fish:
		var cell := VBoxContainer.new()
		cell.custom_minimum_size = Vector2(140, 130)
		var box := PanelContainer.new()
		var sb := U.flat(Color(0.1, 0.14, 0.2, 0.9), Color(0.3, 0.4, 0.5), 2, 6)
		box.add_theme_stylebox_override("panel", sb)
		cell.add_child(box)
		var art := TextureRect.new()
		art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		art.custom_minimum_size = Vector2(140, 78)
		var disc := Game.dex.has(id)
		if disc:
			art.texture = Art.tex(id)
		else:
			art.texture = Art.tex(id)
			art.modulate = Color(0.15, 0.15, 0.2)  # silhouette
		box.add_child(art)
		var f: Dictionary = DB.fish[id]
		var nm := U.label(f["name"] if disc else "???", 13, DB.rarity_color(f["rarity"]))
		nm.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		nm.clip_text = true
		cell.add_child(nm)
		if disc:
			var info := U.label("x%d • %d см" % [Game.dex[id]["count"], Game.dex[id]["best"]], 12, Color(0.8, 0.8, 0.8))
			info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			cell.add_child(info)
		else:
			var season := U.label(_seasons_short(f["seasons"]), 12, Color(0.6, 0.6, 0.7))
			season.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			cell.add_child(season)
		grid.add_child(cell)

func _seasons_short(ss: Array) -> String:
	if ss.size() == 4:
		return "весь год"
	var m := {"0": "В", "1": "Л", "2": "О", "3": "З"}
	var out := ""
	for s in ss:
		out += m[str(s)] + " "
	return out

func _unhandled_input(ev: InputEvent) -> void:
	if _open and (ev.is_action_pressed("dex") or ev.is_action_pressed("menu")):
		close()
		get_viewport().set_input_as_handled()

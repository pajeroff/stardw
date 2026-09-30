extends CanvasLayer
## Daily request board.

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
	if Game.quest.is_empty():
		Game.roll_quest()
	_build()

func close() -> void:
	_open = false
	if _root:
		_root.queue_free()
		_root = null
	closed.emit()

func _progress() -> int:
	return Game.catches_today.get(Game.quest.get("id", ""), 0)

func _build() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.5)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(dim)

	var p := U.panel_container(16)
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.position = Vector2(-220, -170)
	p.size = Vector2(440, 340)
	_root.add_child(p)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	p.add_child(vbox)

	var t := U.label("Доска заказов", 22, Color(1, 0.85, 0.5))
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(t)

	var fish := DB.fish_by_id(Game.quest["id"])
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	vbox.add_child(row)
	row.add_child(U.icon(Game.quest["id"], 48))
	var nm := U.label(" %s" % fish["name"], 20, DB.rarity_color(fish["rarity"]))
	row.add_child(nm)

	var need_lbl := U.label("Нужно поймать сегодня: %d / %d" % [mini(_progress(), Game.quest["need"]), Game.quest["need"]], 16)
	need_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(need_lbl)
	var reward_lbl := U.label("Награда: %d з" % Game.quest["reward"], 16, Color(1, 0.85, 0.4))
	reward_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(reward_lbl)

	var claim := U.button("Забрать награду")
	claim.disabled = _progress() < Game.quest["need"]
	claim.pressed.connect(func():
		Game.add_gold(Game.quest["reward"])
		Sfx.play("coin")
		Game.emit_toast("Заказ выполнен! +%d з" % Game.quest["reward"], Color(1, 0.85, 0.4))
		Game.quest = {}
		close())
	vbox.add_child(claim)

	var close_btn := U.button("Закрыть [E]")
	close_btn.pressed.connect(close)
	vbox.add_child(close_btn)

func _unhandled_input(ev: InputEvent) -> void:
	if _open and (ev.is_action_pressed("interact") or ev.is_action_pressed("menu")):
		close()
		get_viewport().set_input_as_handled()

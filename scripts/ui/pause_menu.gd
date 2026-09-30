extends CanvasLayer
## Pause menu.

const U = preload("res://scripts/ui/ui_util.gd")
signal closed()

var _root: Control = null
var _open := false

func _ready() -> void:
	layer = 40
	process_mode = Node.PROCESS_MODE_ALWAYS

func _unhandled_input(ev: InputEvent) -> void:
	# only active while open (game node is paused and won't also toggle)
	if _open and ev.is_action_pressed("menu"):
		close()
		get_viewport().set_input_as_handled()

func is_open() -> bool:
	return _open

func toggle() -> void:
	if _open:
		close()
	else:
		open()

func open() -> void:
	if _open:
		return
	_open = true
	get_tree().paused = true
	_build()

func close() -> void:
	_open = false
	get_tree().paused = false
	if _root:
		_root.queue_free()
		_root = null
	closed.emit()

func _build() -> void:
	_root = Control.new()
	_root.process_mode = Node.PROCESS_MODE_ALWAYS
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.6)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(dim)

	var p := U.panel_container(18)
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.position = Vector2(-180, -160)
	p.size = Vector2(360, 320)
	_root.add_child(p)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 12)
	p.add_child(vbox)
	var t := U.label("ПАУЗА", 26, Color(1, 0.9, 0.5))
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(t)
	var resume := U.button("Продолжить")
	resume.pressed.connect(close)
	vbox.add_child(resume)
	var save := U.button("Сохранить")
	save.pressed.connect(func(): Game.save(); Game.emit_toast("Сохранено.", Color(0.7, 1, 0.7)))
	vbox.add_child(save)
	var quit := U.button("В главное меню", true)
	quit.pressed.connect(func():
		get_tree().paused = false
		get_tree().change_scene_to_file("res://scenes/main_menu.tscn"))
	vbox.add_child(quit)
	var hint := U.label("WASD/стрелки — ход • ПРОБЕЛ — удочка\nE — взаимодействие • F — каталог\n1..0 — слоты • ESC — пауза", 13, Color(0.75, 0.75, 0.8))
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(hint)

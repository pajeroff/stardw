extends Control
## Main menu.

const U = preload("res://scripts/ui/ui_util.gd")

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	theme = U.theme()
	_build()

func _build() -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.07, 0.12, 0.2)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	# water stripes
	for i in 5:
		var s := ColorRect.new()
		s.color = Color(0.1, 0.25 + i * 0.03, 0.4, 0.5)
		s.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
		s.position = Vector2(0, -i * 40)
		s.size = Vector2(1280, 40)
		add_child(s)

	var vbox := VBoxContainer.new()
	vbox.set_anchors_preset(Control.PRESET_CENTER)
	vbox.position = Vector2(-220, -240)
	vbox.custom_minimum_size = Vector2(440, 480)
	vbox.add_theme_constant_override("separation", 14)
	add_child(vbox)

	var logo := TextureRect.new()
	logo.texture = Art.tex("logo")
	logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	logo.custom_minimum_size = Vector2(0, 90)
	vbox.add_child(logo)

	var sub := U.label("рыбацкая долина", 20, Color(0.7, 0.85, 0.95))
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(sub)

	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 20)
	vbox.add_child(spacer)

	var newb := U.button("Новая игра")
	newb.custom_minimum_size = Vector2(0, 44)
	newb.pressed.connect(func():
		Game.new_game()
		Sfx.play("ui")
		get_tree().change_scene_to_file("res://scenes/game.tscn"))
	vbox.add_child(newb)

	var cont := U.button("Продолжить")
	cont.custom_minimum_size = Vector2(0, 44)
	cont.disabled = not Game.has_save
	cont.pressed.connect(func():
		Game.load_game()
		Sfx.play("ui")
		get_tree().change_scene_to_file("res://scenes/game.tscn"))
	vbox.add_child(cont)

	var hint := U.label("Изометрическая жизнь рыбака:\nлови рыбу, веди каталог, выполняй заказы,\nобустраивайся и открывай легендарных рыб.", 14, Color(0.65, 0.75, 0.85))
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(hint)

	# decorative swimming fish
	var fish := Sprite2D.new()
	fish.texture = Art.tex("carp")
	fish.centered = true
	add_child(fish)
	var tw := create_tween().set_loops()
	tw.tween_property(fish, "position", Vector2(1300, 560), 14.0).from(Vector2(-100, 560))

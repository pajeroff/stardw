extends CanvasLayer
## Big celebratory catch popup.

const U = preload("res://scripts/ui/ui_util.gd")

var _root: Control = null

func _ready() -> void:
	layer = 30
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)

func show_catch(fish_id: String, size_cm: int, price: int, treasure: Array) -> void:
	var fish := DB.fish_by_id(fish_id)
	var first := Game.dex[fish_id]["count"] == 1

	var glow := Sprite2D.new()
	glow.texture = Art.tex("glow_warm")
	glow.centered = true
	glow.position = Vector2(640, 320)
	glow.scale = Vector2(3, 3)
	_root.add_child(glow)

	var p := U.panel_container(16)
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.position = Vector2(-170, -140)
	p.size = Vector2(340, 280)
	_root.add_child(p)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 6)
	p.add_child(vbox)

	var title := U.label("ПОЙМАЛ!", 24, Color(1, 0.85, 0.4))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(title)

	var art := TextureRect.new()
	art.texture = Art.tex(fish_id)
	art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	art.custom_minimum_size = Vector2(0, 120)
	art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vbox.add_child(art)

	var name_lbl := U.label(fish["name"], 20, DB.rarity_color(fish["rarity"]))
	name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(name_lbl)

	var info := U.label("%d см  •  %d з" % [size_cm, price], 16, Color(0.85, 0.85, 0.85))
	info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(info)

	if first:
		var neww := U.label("★ Новый вид в каталог! ★", 15, Color(0.6, 1, 0.7))
		neww.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		vbox.add_child(neww)
	if not treasure.is_empty():
		var tres := U.label("Сокровище: %s" % DB.item_by_id(treasure[0])["name"], 15, Color(1, 0.8, 0.5))
		tres.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		vbox.add_child(tres)

	get_tree().create_timer(2.6).timeout.connect(func():
		p.queue_free()
		glow.queue_free())

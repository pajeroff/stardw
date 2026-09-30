extends CanvasLayer
## Fish shop: buy gear / sell catch.

const U = preload("res://scripts/ui/ui_util.gd")

signal closed()

var _root: Control = null
var _open := false

const BUY := ["rod_bamboo", "rod_fiberglass", "rod_iridium", "bait_worm", "bait_maggot", "bait_shrimp",
			  "bait_glow", "tackle_cork", "tackle_barbed", "tackle_magnet", "lure_spinner", "lure_fly",
			  "lure_trap", "dish_sushi", "dish_grill", "dish_soup", "dish_stew", "coffee"]

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
	dim.color = Color(0, 0, 0, 0.55)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(dim)

	var p := U.panel_container(14)
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.position = Vector2(-430, -260)
	p.size = Vector2(860, 520)
	_root.add_child(p)

	var vbox := VBoxContainer.new()
	p.add_child(vbox)

	var head := HBoxContainer.new()
	vbox.add_child(head)
	head.add_child(U.label("Лавка «Золотой крючок»", 22, Color(1, 0.85, 0.5)))
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(spacer)
	head.add_child(U.icon("ic_gold", 24))
	var gold_lbl := U.label(str(Game.gold), 20, Color(1, 0.85, 0.4))
	head.add_child(gold_lbl)
	Game.gold_changed.connect(func(v): gold_lbl.text = str(v))
	var close_btn := U.button("Закрыть [E]")
	close_btn.pressed.connect(close)
	head.add_child(close_btn)

	var cols := HBoxContainer.new()
	cols.add_theme_constant_override("separation", 14)
	vbox.add_child(cols)

	cols.add_child(_buy_column())
	cols.add_child(_sell_column())

func _buy_column() -> Control:
	var box := VBoxContainer.new()
	box.add_child(U.label("Купить", 18, Color(0.7, 0.9, 0.7)))
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(400, 420)
	box.add_child(scroll)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	for id in BUY:
		var it := DB.item_by_id(id)
		var row := HBoxContainer.new()
		row.add_child(U.icon(id, 26))
		var nm := U.label(it["name"], 14)
		nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(nm)
		row.add_child(U.label("%dз" % it["price"], 14, Color(1, 0.85, 0.4)))
		var b := U.button("Купить")
		b.pressed.connect(func():
			if Game.gold >= it["price"]:
				if Game.add_item(id):
					Game.add_gold(-it["price"])
					Sfx.play("coin")
			else:
				Game.emit_toast("Не хватает золота!", Color(1, 0.6, 0.4))
				Sfx.play("error"))
		row.add_child(b)
		list.add_child(row)
	return box

func _sell_column() -> Control:
	var box := VBoxContainer.new()
	box.add_child(U.label("Продать улов", 18, Color(0.9, 0.7, 0.7)))
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(400, 420)
	box.add_child(scroll)
	var list := VBoxContainer.new()
	list.name = "sell_list"
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	_fill_sell(list)
	return box

func _sell_price(id: String) -> int:
	if DB.fish.has(id):
		return DB.fish[id]["price"]
	return DB.item_by_id(id).get("price", 1)

func _fill_sell(list: VBoxContainer) -> void:
	for ch in list.get_children():
		ch.queue_free()
	var any := false
	for slot in Game.inventory:
		var id: String = slot["id"]
		var typ := DB.item_by_id(id).get("type", "")
		var is_fish := DB.fish.has(id)
		if not (is_fish or typ in ["junk", "treasure", "resource"]):
			continue
		any = true
		var row := HBoxContainer.new()
		row.add_child(U.icon(id, 26))
		var nm := U.label("%s x%d" % [DB.item_by_id(id)["name"] if not is_fish else DB.fish[id]["name"], slot["count"]], 14)
		nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(nm)
		row.add_child(U.label("%dз" % _sell_price(id), 14, Color(1, 0.85, 0.4)))
		var b := U.button("Продать")
		b.pressed.connect(func():
			if Game.remove_item(id, 1):
				Game.add_gold(_sell_price(id))
				Sfx.play("coin")
				_refresh_sell())
		row.add_child(b)
		list.add_child(row)
	if not any:
		list.add_child(U.label("Нечего продавать. Иди рыбачить!", 14, Color(0.7, 0.7, 0.7)))

func _refresh_sell() -> void:
	if _root == null:
		return
	var list := _root.find_child("sell_list", true, false)
	if list:
		_fill_sell(list)

func _unhandled_input(ev: InputEvent) -> void:
	if _open and (ev.is_action_pressed("interact") or ev.is_action_pressed("menu")):
		close()
		get_viewport().set_input_as_handled()

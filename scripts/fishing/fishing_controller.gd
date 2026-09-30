extends Node
## FishingController: cast / wait / bite / minigame / result loop.

signal catch_happened(fish_id: String, size_cm: int, price: int)
signal popup_catch(fish_id: String, size_cm: int, price: int, treasure: Array)

const IsoS = preload("res://scripts/world/iso.gd")
const MiniS = preload("res://scripts/fishing/minigame.gd")

var player = null
var world = null

var state := "idle"
var bobber: Sprite2D = null
var excl: Sprite2D = null
var water_cell := Vector2i.ZERO
var _wait_t := 0.0
var _bite_window := 0.0
var _nibble_t := 0.0

func _ready() -> void:
	player.request_fish.connect(_on_fish)

func _on_fish() -> void:
	if state != "idle":
		return
	_try_cast()

func _try_cast() -> void:
	if Game.rod_id == "":
		Game.emit_toast("Нужна удочка!", Color(1, 0.6, 0.4))
		return
	if not Game.spend_energy(2):
		return
	var cell := player._cell()
	var target := world.fishing_cell_from(cell, player.facing)
	if not world.map.is_water(target):
		Game.emit_toast("Здесь нет воды.", Color(0.8, 0.8, 0.8))
		Game.restore_energy(2)
		return
	water_cell = target
	player.locked = true
	player.set_override("cast_" + player.dir_name)
	Sfx.play("cast")
	# bait
	if Game.bait_id != "":
		Game.remove_item(Game.bait_id, 1)
	# place bobber after short cast anim
	get_tree().create_timer(0.35).timeout.connect(func():
		_spawn_bobber()
		state = "waiting"
		_compute_wait()
		Sfx.play("splash")
		player.set_override("hold_" + player.dir_name))

func _compute_wait() -> void:
	var base := randf_range(2.0, 6.0)
	var bait: float = float(DB.item_by_id(Game.bait_id).get("bite", 1.0))
	if Game.weather == "rain":
		base *= 0.8
	if Game.is_night() and DB.item_by_id(Game.bait_id).get("night", false):
		base *= 0.7
	_wait_t = base * bait

func _spawn_bobber() -> void:
	bobber = Sprite2D.new()
	bobber.texture = Art.tex("bobber_0")
	bobber.centered = false
	var l := IsoS.cell_to_local(water_cell)
	bobber.position = Vector2(l.x - 6, l.y + 8)
	world.add_child(bobber)
	excl = Sprite2D.new()
	excl.texture = Art.tex("exclam")
	excl.centered = true
	excl.visible = false
	excl.position = Vector2(l.x, l.y - 20)
	world.add_child(excl)

func _process(delta: float) -> void:
	if state == "waiting":
		_wait_t -= delta
		_nibble_t += delta
		# gentle bob
		var dip := 0 if fmod(_nibble_t, 1.0) > 0.2 else 1
		bobber.texture = Art.tex("bobber_%d" % dip)
		if _wait_t <= 0:
			_start_bite()
	elif state == "bite":
		_bite_window -= delta
		bobber.texture = Art.tex("bobber_1")
		if Input.is_action_just_pressed("use"):
			_hook()
		elif _bite_window <= 0:
			_miss()

func _start_bite() -> void:
	state = "bite"
	_bite_window = 0.9
	excl.visible = true
	Sfx.play("bite")

func _hook() -> void:
	excl.visible = false
	_start_minigame()

func _miss() -> void:
	Game.emit_toast("Сорвалась! Нажимай ПРОБЕЛ вовремя.", Color(0.9, 0.8, 0.5))
	_cleanup()

func _start_minigame() -> void:
	state = "minigame"
	var chosen := choose_fish()
	var fish := DB.fish_by_id(chosen)
	var diff := float(fish.get("diff", 2))
	var tackle := DB.item_by_id(Game.tackle_id)
	var bar_mult: float = float(tackle.get("bar", 1.0))
	var tres_mult: float = float(tackle.get("treasure", 1.0))
	var mini = MiniS.new()
	add_child(mini)
	mini.start(diff, bar_mult, tackle.get("grip", 1.0), tres_mult)
	mini.finished.connect(func(success, treasure):
		_on_result(success, treasure, chosen, fish))

func choose_fish() -> String:
	var water := world.water_type_at(water_cell)
	var pool: Array = []
	var weights: Array = []
	for id in DB.fish:
		var f = DB.fish[id]
		if not f["water"].has(water):
			continue
		if not f["seasons"].has(Game.season):
			continue
		if f["tod"] != "any":
			if f["tod"] == "night" and not Game.is_night():
				continue
			if f["tod"] == "day" and Game.is_night():
				continue
		if f["weather"] != "any" and f["weather"] != Game.weather:
			continue
		var w := DB.rarity_weight(f["rarity"], Game.luck())
		if Game.lure_id != "" and f["rarity"] in ["rare", "legendary"]:
			w *= DB.item_by_id(Game.lure_id).get("rare", 1.0)
		pool.append(id)
		weights.append(w)
	if pool.is_empty():
		return "roach"
	var total := 0.0
	for w in weights:
		total += w
	var r := randf() * total
	for i in pool.size():
		r -= weights[i]
		if r <= 0:
			return pool[i]
	return pool[pool.size() - 1]

func _on_result(success: bool, treasure: bool, fish_id: String, fish: Dictionary) -> void:
	_cleanup()
	var tres_items: Array = []
	if treasure:
		tres_items = _roll_treasure()
	if not success:
		Game.emit_toast("Рыба сорвалась с крючка...", Color(0.7, 0.8, 1.0))
		if not tres_items.is_empty():
			for t in tres_items:
				Game.add_item(t)
		return
	# junk chance
	if randf() < 0.10:
		var junk := ["junk_boot", "junk_can", "junk_seaweed", "junk_driftwood"][randi() % 4]
		Game.add_item(junk)
		Game.emit_toast("Поймался мусор: %s" % DB.item_by_id(junk)["name"], Color(0.7, 0.7, 0.7))
		Sfx.play("splash")
	else:
		var size := randi_range(fish["size"][0], fish["size"][1])
		var price: int = int(fish["price"])
		Game.record_catch(fish_id, size)
		Game.add_item(fish_id)
		Sfx.play("catch")
		catch_happened.emit(fish_id, size, price)
		popup_catch.emit(fish_id, size, price, tres_items)
	for t in tres_items:
		Game.add_item(t)

func _roll_treasure() -> Array:
	var opts := ["treasure_pearl", "treasure_ring", "treasure_emerald", "treasure_sapphire", "treasure_ruby", "treasure_idol", "treasure_crown"]
	return [opts[randi() % opts.size()]]

func _cleanup() -> void:
	state = "idle"
	if bobber:
		bobber.queue_free()
		bobber = null
	if excl:
		excl.queue_free()
		excl = null
	player.locked = false
	player.set_override("")

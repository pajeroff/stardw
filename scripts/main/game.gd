extends Node2D
## Game root: wires world, player, camera, fishing, UI, clock and music.

const WorldS = preload("res://scripts/world/world.gd")
const PlayerS = preload("res://scripts/world/player.gd")
const DayNightS = preload("res://scripts/world/day_night.gd")
const WeatherS = preload("res://scripts/world/weather.gd")
const FishCtlS = preload("res://scripts/fishing/fishing_controller.gd")
const HudS = preload("res://scripts/ui/hud.gd")
const PopupS = preload("res://scripts/ui/catch_popup.gd")
const ShopS = preload("res://scripts/ui/shop.gd")
const DexS = preload("res://scripts/ui/fish_dex.gd")
const BoardS = preload("res://scripts/ui/board.gd")
const PauseS = preload("res://scripts/ui/pause_menu.gd")

var world = null
var player = null
var camera: Camera2D = null
var hud = null
var fishing = null
var shop = null
var dex = null
var board = null
var pause = null
var popup = null

var _clock_acc := 0.0
const REAL_SEC_PER_MIN := 0.7
var _music := ""

func _ready() -> void:
	world = Node2D.new()
	world.set_script(WorldS)
	add_child(world)

	player = Node2D.new()
	player.set_script(PlayerS)
	player.world = world
	world.entities.add_child(player)

	camera = Camera2D.new()
	camera.position_smoothing_enabled = true
	camera.position_smoothing_speed = 6.0
	add_child(camera)

	var dn = CanvasModulate.new()
	dn.set_script(DayNightS)
	add_child(dn)

	var weather = CanvasLayer.new()
	weather.set_script(WeatherS)
	add_child(weather)

	fishing = Node.new()
	fishing.set_script(FishCtlS)
	fishing.player = player
	fishing.world = world
	add_child(fishing)

	popup = CanvasLayer.new()
	popup.set_script(PopupS)
	add_child(popup)
	fishing.popup_catch.connect(func(id, size, price, tres): popup.show_catch(id, size, price, tres))

	hud = CanvasLayer.new()
	hud.set_script(HudS)
	hud.player = player
	hud.world = world
	add_child(hud)

	shop = CanvasLayer.new()
	shop.set_script(ShopS)
	add_child(shop)
	dex = CanvasLayer.new()
	dex.set_script(DexS)
	add_child(dex)
	board = CanvasLayer.new()
	board.set_script(BoardS)
	add_child(board)
	pause = CanvasLayer.new()
	pause.set_script(PauseS)
	add_child(pause)

	player.request_interact.connect(_on_interact)
	Game.day_changed.connect(func(_d, _s, _y): _update_music())
	_update_music()

func _any_ui_open() -> bool:
	return shop.is_open() or dex.is_open() or board.is_open() or pause.is_open()

func _on_interact(kind: String) -> void:
	match kind:
		"shop":
			Sfx.play("ui")
			shop.open()
		"board":
			Sfx.play("page")
			board.open()
		"house":
			Sfx.play("sleep")
			Game.sleep(false)
		"campfire":
			Game.restore_energy(10)
			Game.emit_toast("Отдых у костра: +10 энергии", Color(1, 0.8, 0.5))
		"well":
			Game.emit_toast("Вода в колодце ледяная.", Color(0.7, 0.85, 1))
		"boat":
			Game.emit_toast("Лодка пока не на ходу...", Color(0.8, 0.8, 0.8))

func _unhandled_input(ev: InputEvent) -> void:
	if ev.is_action_pressed("menu"):
		if shop.is_open() or dex.is_open() or board.is_open():
			return  # their own handlers close
		pause.toggle()
		get_viewport().set_input_as_handled()
	elif ev.is_action_pressed("dex") and not pause.is_open():
		if dex.is_open():
			dex.close()
		else:
			Sfx.play("page")
			dex.open()
		get_viewport().set_input_as_handled()

func _process(delta: float) -> void:
	camera.position = camera.position.lerp(player.position, 0.2)
	if _any_ui_open():
		return
	_clock_acc += delta
	while _clock_acc >= REAL_SEC_PER_MIN:
		_clock_acc -= REAL_SEC_PER_MIN
		Game.advance_time(1)
	_update_music()

func _update_music() -> void:
	var want := "day"
	if Game.is_night():
		want = "night"
	elif Game.weather in ["rain", "storm", "snow"]:
		want = "rain"
	if want != _music:
		_music = want
		Sfx.play_music(want)

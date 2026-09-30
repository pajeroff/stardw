extends Node2D
## Player: 8-way isometric movement, sprite animation and interaction.

signal request_fish()
signal request_interact(kind: String)
signal moved(cell: Vector2i)

const IsoS = preload("res://scripts/world/iso.gd")

@export var speed := 220.0

var world = null
var sprite: Sprite2D = null
var shadow: Sprite2D = null

var facing := Vector2(0, 1)        # screen-space facing
var dir_name := "down"
var _override: String = ""
var _anim := ""
var _frames: Array = []
var _fps := 8.0
var _acc := 0.0
var _frame := 0
var _step_acc := 0.0
var locked := false                # while fishing / in UI

func _ready() -> void:
	shadow = Sprite2D.new()
	shadow.texture = Art.tex("shadow")
	shadow.centered = true
	shadow.position = Vector2(0, -2)
	shadow.scale = Vector2(0.6, 0.6)
	add_child(shadow)
	sprite = Sprite2D.new()
	sprite.centered = false
	add_child(sprite)
	_set_anim("idle_down")
	position = IsoS.cell_to_local(world.map.player_start) + Vector2(0, 16)

func set_override(name: String) -> void:
	_override = name
	if name != "":
		_set_anim(name)
	else:
		_set_anim("idle_" + dir_name)

func _set_anim(name: String) -> void:
	if not Art.manifest["anims"].has(name):
		return
	if _anim == name:
		return
	_anim = name
	var fr = Art.frames(name)
	_frames = fr[0]
	_fps = fr[1]
	_frame = 0
	_acc = 0.0
	_apply_frame()

func _apply_frame() -> void:
	if _frames.is_empty():
		return
	var tex = _frames[_frame % _frames.size()]
	sprite.texture = tex
	sprite.centered = false
	sprite.offset = Vector2(0, 0)
	# anchor bottom-center
	sprite.position = Vector2(-tex.get_width() * 0.5, -tex.get_height() + 4)

func _unhandled_input(ev: InputEvent) -> void:
	if locked:
		return
	if ev.is_action_pressed("interact"):
		var kind := world.interactable_near(_cell())
		if kind != "":
			request_interact.emit(kind)
	if ev.is_action_pressed("use"):
		request_fish.emit()

func _cell() -> Vector2i:
	return world.cell_at(position)

func _physics_process(delta: float) -> void:
	_advance_anim(delta)
	if locked:
		return
	var v := Vector2.ZERO
	if Input.is_action_pressed("move_up"):
		v += Vector2(0, -1)
	if Input.is_action_pressed("move_down"):
		v += Vector2(0, 1)
	if Input.is_action_pressed("move_left"):
		v += Vector2(-1, 0)
	if Input.is_action_pressed("move_right"):
		v += Vector2(1, 0)
	if v != Vector2.ZERO:
		v = v.normalized()
		facing = v
		_update_dir(v)
		var target := position + v * speed * delta
		_move_with_collision(target)
		_set_anim("walk_" + dir_name)
		_step_acc += speed * delta
		if _step_acc > 34.0:
			_step_acc = 0.0
			Sfx.play("step", randf_range(0.9, 1.1), 0.4)
		moved.emit(_cell())
	else:
		_set_anim("idle_" + dir_name)

func _update_dir(v: Vector2) -> void:
	if absf(v.x) > absf(v.y):
		dir_name = "right" if v.x > 0 else "left"
	else:
		dir_name = "down" if v.y > 0 else "up"

func _move_with_collision(target: Vector2) -> void:
	var cur := _cell()
	# try full move
	if world.is_walkable(world.cell_at(target)):
		position = target
		return
	# slide x
	var tx := Vector2(target.x, position.y)
	if world.is_walkable(world.cell_at(tx)):
		position.x = target.x
		return
	# slide y
	var ty := Vector2(position.x, target.y)
	if world.is_walkable(world.cell_at(ty)):
		position.y = target.y

func _advance_anim(delta: float) -> void:
	if _frames.size() <= 1:
		return
	_acc += delta
	var step := 1.0 / _fps
	while _acc >= step:
		_acc -= step
		_frame = (_frame + 1) % _frames.size()
		_apply_frame()

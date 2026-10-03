extends CharacterBody2D
class_name Player

signal state_changed(anim_state: String, dir_name: String, dir_vector: Vector2)
signal tool_changed(tool_index: int, tool_id: String, tool_title: String)
signal tool_used(tool_id: String, target_global_pos: Vector2, facing_dir: Vector2)

@export var walk_speed: float = 150.0
@export var run_speed: float = 250.0
@export var acceleration: float = 1050.0
@export var friction: float = 1200.0

# Order of directions matches rows in assets/sprites/player_spritesheet.png (96x96 frames)
const DIRECTIONS: Array[String] = [
	"down",        # 0: S  (Вниз)
	"down_right",  # 1: SE (Вниз-Вправо)
	"right",       # 2: E  (Вправо)
	"up_right",    # 3: NE (Вверх-Вправо)
	"up",          # 4: N  (Вверх)
	"up_left",     # 5: NW (Вверх-Влево)
	"left",        # 6: W  (Влево)
	"down_left",   # 7: SW (Вниз-Влево)
]

const DIRECTION_VECTORS: Dictionary = {
	"down": Vector2(0.0, 1.0),
	"down_right": Vector2(0.89442719, 0.4472136),
	"right": Vector2(1.0, 0.0),
	"up_right": Vector2(0.89442719, -0.4472136),
	"up": Vector2(0.0, -1.0),
	"up_left": Vector2(-0.89442719, -0.4472136),
	"left": Vector2(-1.0, 0.0),
	"down_left": Vector2(-0.89442719, 0.4472136),
}

const DIRECTION_LABELS_RU: Dictionary = {
	"down": "Юг (Вниз)",
	"down_right": "ЮВ (Изометрия Вниз-Вправо)",
	"right": "Восток (Вправо)",
	"up_right": "СВ (Изометрия Вверх-Вправо)",
	"up": "Север (Вверх)",
	"up_left": "СЗ (Изометрия Вверх-Влево)",
	"left": "Запад (Влево)",
	"down_left": "ЮЗ (Изометрия Вниз-Влево)",
}

# Animation table matching player_spritesheet.png (56 rows x 8 columns, 96x96 per frame)
const ANIM_CONFIG: Dictionary = {
	"idle":     {"base_row": 0,  "frames": 8, "fps": 7.0,  "loop": true},
	"walk":     {"base_row": 8,  "frames": 8, "fps": 10.5, "loop": true},
	"run":      {"base_row": 16, "frames": 8, "fps": 14.0, "loop": true},
	"axe":      {"base_row": 24, "frames": 8, "fps": 13.0, "loop": false},
	"pickaxe":  {"base_row": 32, "frames": 8, "fps": 13.0, "loop": false},
	"water":    {"base_row": 40, "frames": 8, "fps": 12.0, "loop": false},
	"interact": {"base_row": 48, "frames": 8, "fps": 11.0, "loop": false},
}

const TOOLS: Array[Dictionary] = [
	{"id": "axe",      "title": "Рубка дерева"},
	{"id": "pickaxe",  "title": "Разбор камня"},
	{"id": "water",    "title": "Полив почвы"},
	{"id": "interact", "title": "Сбор / Осмотр"},
]

const DIAGONAL_GRACE_TIME: float = 0.085

@onready var sprite: Sprite2D = $Sprite2D
@onready var anim_player: AnimationPlayer = $AnimationPlayer
@onready var anim_tree: AnimationTree = $AnimationTree
@onready var interaction_area: Area2D = $InteractionArea
@onready var collision_shape: CollisionShape2D = $CollisionShape2D

var facing_name: String = "down_right"
var facing_vector: Vector2 = Vector2(0.89442719, 0.4472136)
var current_state: String = "idle"
var current_tool_index: int = 0

var is_performing_action: bool = false
var action_timer: float = 0.0
var action_duration: float = 0.0
var action_hit_triggered: bool = false
var active_action_id: String = ""

var _last_diagonal_name: String = ""
var _diagonal_grace_timer: float = 0.0
var debug_draw_enabled: bool = false


func _ready() -> void:
	_build_all_8dir_animations()
	_setup_animation_tree()
	_play_8dir_animation("idle", facing_name)
	_update_interaction_transform()
	tool_changed.emit(current_tool_index, TOOLS[current_tool_index]["id"], TOOLS[current_tool_index]["title"])
	state_changed.emit(current_state, facing_name, facing_vector)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("tool_1"):
		select_tool(0)
	elif event.is_action_pressed("tool_2"):
		select_tool(1)
	elif event.is_action_pressed("tool_3"):
		select_tool(2)
	elif event.is_action_pressed("tool_4"):
		select_tool(3)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			select_tool((current_tool_index - 1 + TOOLS.size()) % TOOLS.size())
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			select_tool((current_tool_index + 1) % TOOLS.size())

	if not is_performing_action:
		if event.is_action_pressed("use_tool"):
			if event is InputEventMouseButton:
				var to_mouse: Vector2 = get_global_mouse_position() - global_position
				if to_mouse.length_squared() > 9.0:
					_set_facing_from_vector(to_mouse.normalized(), true)
			start_tool_action(TOOLS[current_tool_index]["id"])
		elif event.is_action_pressed("interact"):
			start_tool_action("interact")


func select_tool(index: int) -> void:
	current_tool_index = clampi(index, 0, TOOLS.size() - 1)
	tool_changed.emit(current_tool_index, TOOLS[current_tool_index]["id"], TOOLS[current_tool_index]["title"])


func start_tool_action(action_id: String) -> void:
	if is_performing_action or not ANIM_CONFIG.has(action_id):
		return
	is_performing_action = true
	active_action_id = action_id
	action_hit_triggered = false
	var cfg: Dictionary = ANIM_CONFIG[action_id]
	action_duration = float(cfg["frames"]) / float(cfg["fps"])
	action_timer = 0.0
	_update_interaction_transform()
	_play_8dir_animation(action_id, facing_name)


func _physics_process(delta: float) -> void:
	if _diagonal_grace_timer > 0.0:
		_diagonal_grace_timer -= delta

	if is_performing_action:
		velocity = velocity.move_toward(Vector2.ZERO, friction * delta)
		move_and_slide()
		action_timer += delta

		if not action_hit_triggered and action_timer >= action_duration * 0.52:
			action_hit_triggered = true
			var reach_pos: Vector2 = global_position + Vector2(0, -8) + facing_vector.normalized() * 38.0
			tool_used.emit(active_action_id, reach_pos, facing_vector.normalized())

		if action_timer >= action_duration:
			is_performing_action = false
			active_action_id = ""
			_play_8dir_animation("idle", facing_name)

		if debug_draw_enabled:
			queue_redraw()
		return

	var raw_x: float = Input.get_axis("move_left", "move_right")
	var raw_y: float = Input.get_axis("move_up", "move_down")
	var input_vec := Vector2(raw_x, raw_y)

	if input_vec.length_squared() > 0.01:
		# For isometric movement, diagonal movement uses 2:1 isometric slope (dx, dy * 0.65)
		var iso_move_vec := Vector2(input_vec.x, input_vec.y * (0.65 if absf(input_vec.x) > 0.1 else 1.0)).normalized()
		_set_facing_from_vector(input_vec.normalized(), false)
		_update_interaction_transform()

		var is_running: bool = Input.is_action_pressed("sprint")
		var target_speed: float = run_speed if is_running else walk_speed
		velocity = velocity.move_toward(iso_move_vec * target_speed, acceleration * delta)

		var target_anim: String = "run" if is_running else "walk"
		_play_8dir_animation(target_anim, facing_name)
	else:
		velocity = velocity.move_toward(Vector2.ZERO, friction * delta)
		_play_8dir_animation("idle", facing_name)

	move_and_slide()

	if debug_draw_enabled:
		queue_redraw()


func _set_facing_from_vector(vec: Vector2, immediate: bool) -> void:
	var candidate: String = vector_to_direction_name(vec)
	var is_diag: bool = candidate.contains("_")

	if is_diag:
		_last_diagonal_name = candidate
		_diagonal_grace_timer = DIAGONAL_GRACE_TIME
		facing_name = candidate
	else:
		if not immediate and _diagonal_grace_timer > 0.0 and _last_diagonal_name != "":
			facing_name = _last_diagonal_name
		else:
			facing_name = candidate

	facing_vector = DIRECTION_VECTORS[facing_name]


static func vector_to_direction_name(vec: Vector2) -> String:
	var angle: float = atan2(vec.y, vec.x)
	var sector: int = int(round(angle / (PI / 4.0)))
	match sector:
		0:
			return "right"
		1:
			return "down_right"
		2:
			return "down"
		3:
			return "down_left"
		4, -4:
			return "left"
		-3:
			return "up_left"
		-2:
			return "up"
		-1:
			return "up_right"
		_:
			return "down_right"


func _update_interaction_transform() -> void:
	if interaction_area:
		interaction_area.position = Vector2(0, -8) + facing_vector.normalized() * 38.0


func _play_8dir_animation(state_name: String, dir_name: String) -> void:
	var full_anim_name: String = "%s_%s" % [state_name, dir_name]
	var same_state: bool = (state_name == current_state)
	var changed: bool = (state_name != current_state) or (dir_name != facing_name)
	current_state = state_name

	if anim_tree and anim_tree.active:
		var blend_vec: Vector2 = DIRECTION_VECTORS.get(dir_name, Vector2.DOWN).normalized()
		anim_tree.set("parameters/Idle/blend_position", blend_vec)
		anim_tree.set("parameters/Walk/blend_position", blend_vec)
		anim_tree.set("parameters/Run/blend_position", blend_vec)
		anim_tree.set("parameters/Axe/blend_position", blend_vec)
		anim_tree.set("parameters/Pickaxe/blend_position", blend_vec)
		anim_tree.set("parameters/Water/blend_position", blend_vec)
		anim_tree.set("parameters/Interact/blend_position", blend_vec)

	if anim_player and anim_player.has_animation(full_anim_name):
		if anim_player.current_animation != full_anim_name:
			var prev_pos: float = 0.0
			if same_state and anim_player.is_playing():
				prev_pos = anim_player.current_animation_position
			anim_player.play(full_anim_name)
			if same_state and prev_pos > 0.0:
				var anim_res: Animation = anim_player.get_animation(full_anim_name)
				if anim_res and anim_res.length > 0.0:
					anim_player.seek(fposmod(prev_pos, anim_res.length), true)

	if changed:
		state_changed.emit(current_state, facing_name, facing_vector)


func _build_all_8dir_animations() -> void:
	var library := AnimationLibrary.new()
	var cols: int = sprite.hframes

	for state_name in ANIM_CONFIG.keys():
		var cfg: Dictionary = ANIM_CONFIG[state_name]
		var base_row: int = cfg["base_row"]
		var frame_count: int = cfg["frames"]
		var fps: float = cfg["fps"]
		var is_loop: bool = cfg["loop"]

		for dir_idx in range(DIRECTIONS.size()):
			var dir_name: String = DIRECTIONS[dir_idx]
			var row: int = base_row + dir_idx
			var anim := Animation.new()
			var step: float = 1.0 / fps
			anim.length = frame_count * step
			anim.loop_mode = Animation.LOOP_LINEAR if is_loop else Animation.LOOP_NONE

			var track_idx: int = anim.add_track(Animation.TYPE_VALUE)
			anim.track_set_path(track_idx, NodePath("Sprite2D:frame"))
			anim.value_track_set_update_mode(track_idx, Animation.UPDATE_DISCRETE)

			for f in range(frame_count):
				var frame_index: int = row * cols + f
				anim.track_insert_key(track_idx, f * step, frame_index)

			library.add_animation("%s_%s" % [state_name, dir_name], anim)

	if anim_player.has_animation_library(""):
		anim_player.remove_animation_library("")
	anim_player.add_animation_library("", library)


func _setup_animation_tree() -> void:
	if not anim_tree:
		return
	var state_machine := AnimationNodeStateMachine.new()
	var state_mapping: Dictionary = {
		"Idle": "idle",
		"Walk": "walk",
		"Run": "run",
		"Axe": "axe",
		"Pickaxe": "pickaxe",
		"Water": "water",
		"Interact": "interact",
	}

	for node_title in state_mapping.keys():
		var prefix: String = state_mapping[node_title]
		var bs2d := AnimationNodeBlendSpace2D.new()
		bs2d.blend_mode = AnimationNodeBlendSpace2D.BLEND_MODE_DISCRETE
		for dir_name in DIRECTIONS:
			var anim_node := AnimationNodeAnimation.new()
			anim_node.animation = "%s_%s" % [prefix, dir_name]
			var pt: Vector2 = DIRECTION_VECTORS[dir_name].normalized()
			bs2d.add_blend_point(anim_node, pt)
		state_machine.add_node(node_title, bs2d)

	anim_tree.tree_root = state_machine
	anim_tree.anim_player = anim_tree.get_path_to(anim_player)
	anim_tree.active = false


func get_direction_label_ru() -> String:
	return DIRECTION_LABELS_RU.get(facing_name, facing_name)


func set_debug_draw(enabled: bool) -> void:
	debug_draw_enabled = enabled
	queue_redraw()


func _draw() -> void:
	if not debug_draw_enabled:
		return
	var col_rect := Rect2(Vector2(-12, -16), Vector2(24, 16))
	draw_rect(col_rect, Color(0.1, 0.95, 1.0, 0.42), true)
	draw_rect(col_rect, Color(0.0, 1.0, 1.0, 0.95), false, 1.5)
	var origin := Vector2(0, -8)
	var tip: Vector2 = origin + facing_vector.normalized() * 38.0
	draw_line(origin, tip, Color(1.0, 0.9, 0.2, 0.95), 2.0)
	draw_circle(tip, 16.0, Color(1.0, 0.35, 0.2, 0.32))
	draw_arc(tip, 16.0, 0.0, TAU, 24, Color(1.0, 0.45, 0.2, 0.9), 1.5)

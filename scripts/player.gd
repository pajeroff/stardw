extends CharacterBody2D
class_name Player

signal state_changed(anim_state: String, dir_name: String, dir_vector: Vector2)
signal tool_changed(tool_index: int, tool_id: String, tool_title: String)
signal tool_used(tool_id: String, target_global_pos: Vector2, facing_dir: Vector2)

@export var walk_speed: float = 95.0
@export var run_speed: float = 165.0
@export var acceleration: float = 950.0
@export var friction: float = 1150.0

# Order of directions matches rows in assets/sprites/player_spritesheet.png
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
	"down": Vector2(0, 1),
	"down_right": Vector2(1, 1),
	"right": Vector2(1, 0),
	"up_right": Vector2(1, -1),
	"up": Vector2(0, -1),
	"up_left": Vector2(-1, -1),
	"left": Vector2(-1, 0),
	"down_left": Vector2(-1, 1),
}

const DIRECTION_LABELS_RU: Dictionary = {
	"down": "Вниз (Ю)",
	"down_right": "Вниз-Вправо (ЮВ)",
	"right": "Вправо (В)",
	"up_right": "Вверх-Вправо (СВ)",
	"up": "Вверх (С)",
	"up_left": "Вверх-Влево (СЗ)",
	"left": "Влево (З)",
	"down_left": "Вниз-Влево (ЮЗ)",
}

# Animation table matching player_spritesheet.png (56 rows x 6 columns)
const ANIM_CONFIG: Dictionary = {
	"idle":     {"base_row": 0,  "frames": 4, "fps": 6.0,  "loop": true},
	"walk":     {"base_row": 8,  "frames": 6, "fps": 10.0, "loop": true},
	"run":      {"base_row": 16, "frames": 6, "fps": 15.0, "loop": true},
	"axe":      {"base_row": 24, "frames": 6, "fps": 14.0, "loop": false},
	"pickaxe":  {"base_row": 32, "frames": 6, "fps": 14.0, "loop": false},
	"water":    {"base_row": 40, "frames": 6, "fps": 12.0, "loop": false},
	"interact": {"base_row": 48, "frames": 4, "fps": 10.0, "loop": false},
}

const TOOLS: Array[Dictionary] = [
	{"id": "axe",      "title": "Топор (Рубка леса)"},
	{"id": "pickaxe",  "title": "Кирка (Добыча камня)"},
	{"id": "water",    "title": "Лейка (Полив земли)"},
	{"id": "interact", "title": "Рука (Сбор / Действие)"},
]

const DIAGONAL_GRACE_TIME: float = 0.065

@onready var sprite: Sprite2D = $Sprite2D
@onready var anim_player: AnimationPlayer = $AnimationPlayer
@onready var anim_tree: AnimationTree = $AnimationTree
@onready var interaction_area: Area2D = $InteractionArea
@onready var collision_shape: CollisionShape2D = $CollisionShape2D

var facing_name: String = "down"
var facing_vector: Vector2 = Vector2(0, 1)
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
				if to_mouse.length_squared() > 4.0:
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

		# Trigger world hit / interaction at ~55% of swing animation
		if not action_hit_triggered and action_timer >= action_duration * 0.52:
			action_hit_triggered = true
			var reach_pos: Vector2 = global_position + Vector2(0, 6) + facing_vector.normalized() * 16.0
			tool_used.emit(active_action_id, reach_pos, facing_vector.normalized())

		if action_timer >= action_duration:
			is_performing_action = false
			active_action_id = ""
			_play_8dir_animation("idle", facing_name)

		if debug_draw_enabled:
			queue_redraw()
		return

	# Read raw 8-way input vector
	var raw_x: float = Input.get_axis("move_left", "move_right")
	var raw_y: float = Input.get_axis("move_up", "move_down")
	var input_vec := Vector2(raw_x, raw_y)

	if input_vec.length_squared() > 0.01:
		var norm_vec: Vector2 = input_vec.normalized()
		_set_facing_from_vector(norm_vec, false)
		_update_interaction_transform()

		var is_running: bool = Input.is_action_pressed("sprint")
		var target_speed: float = run_speed if is_running else walk_speed
		velocity = velocity.move_toward(norm_vec * target_speed, acceleration * delta)

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
		# Preserve diagonal direction if player is in the middle of releasing two keys
		if not immediate and _diagonal_grace_timer > 0.0 and _last_diagonal_name != "":
			facing_name = _last_diagonal_name
		else:
			facing_name = candidate

	facing_vector = DIRECTION_VECTORS[facing_name]


static func vector_to_direction_name(vec: Vector2) -> String:
	# Convert angle to 8 sectors of 45 degrees (PI / 4)
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
			return "down"


func _update_interaction_transform() -> void:
	if interaction_area:
		interaction_area.position = Vector2(0, 6) + facing_vector.normalized() * 14.0


func _play_8dir_animation(state_name: String, dir_name: String) -> void:
	var full_anim_name: String = "%s_%s" % [state_name, dir_name]
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
			anim_player.play(full_anim_name)

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
	var state_Mapping: Dictionary = {
		"Idle": "idle",
		"Walk": "walk",
		"Run": "run",
		"Axe": "axe",
		"Pickaxe": "pickaxe",
		"Water": "water",
		"Interact": "interact",
	}

	for node_title in state_Mapping.keys():
		var prefix: String = state_Mapping[node_title]
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
	# Keep direct AnimationPlayer control crisp and deterministic
	anim_tree.active = false


func get_direction_label_ru() -> String:
	return DIRECTION_LABELS_RU.get(facing_name, facing_name)


func set_debug_draw(enabled: bool) -> void:
	debug_draw_enabled = enabled
	queue_redraw()


func _draw() -> void:
	if not debug_draw_enabled:
		return
	# Draw feet collision circle
	draw_circle(Vector2(0, 10), 5.0, Color(0.1, 0.95, 1.0, 0.42))
	draw_arc(Vector2(0, 10), 5.0, 0.0, TAU, 24, Color(0.0, 1.0, 1.0, 0.95), 1.2)
	# Draw 8-direction vector arrow & interaction hitbox
	var origin := Vector2(0, 6)
	var tip: Vector2 = origin + facing_vector.normalized() * 16.0
	draw_line(origin, tip, Color(1.0, 0.9, 0.2, 0.95), 1.5)
	draw_circle(tip, 5.5, Color(1.0, 0.35, 0.2, 0.35))
	draw_arc(tip, 5.5, 0.0, TAU, 20, Color(1.0, 0.45, 0.2, 0.9), 1.0)

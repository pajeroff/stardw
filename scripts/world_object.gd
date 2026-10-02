extends StaticBody2D
class_name WorldObject

signal resource_dropped(resource_type: String, amount: int, world_pos: Vector2)

@export var object_type: String = "tree_oak"

const OBJECT_DEFS: Dictionary = {
	"tree_oak": {
		"texture": "res://assets/objects/tree_oak.png",
		"sprite_offset": Vector2(0, -18),
		"collision_size": Vector2(16, 16),
		"collision_offset": Vector2(0, -5),
		"hp": 3,
		"tool": "axe",
		"drop_type": "wood",
		"drop_amount": 3,
		"becomes_stump": true,
	},
	"tree_pine": {
		"texture": "res://assets/objects/tree_pine.png",
		"sprite_offset": Vector2(0, -18),
		"collision_size": Vector2(16, 16),
		"collision_offset": Vector2(0, -5),
		"hp": 3,
		"tool": "axe",
		"drop_type": "wood",
		"drop_amount": 3,
		"becomes_stump": true,
	},
	"tree_birch": {
		"texture": "res://assets/objects/tree_birch.png",
		"sprite_offset": Vector2(0, -18),
		"collision_size": Vector2(15, 16),
		"collision_offset": Vector2(0, -5),
		"hp": 3,
		"tool": "axe",
		"drop_type": "wood",
		"drop_amount": 3,
		"becomes_stump": true,
	},
	"tree_stump": {
		"texture": "res://assets/objects/tree_stump.png",
		"sprite_offset": Vector2(0, -4),
		"collision_size": Vector2(12, 10),
		"collision_offset": Vector2(0, -2),
		"hp": 2,
		"tool": "axe",
		"drop_type": "wood",
		"drop_amount": 1,
		"becomes_stump": false,
	},
	"log_fallen": {
		"texture": "res://assets/objects/log_fallen.png",
		"sprite_offset": Vector2(0, -4),
		"collision_size": Vector2(28, 11),
		"collision_offset": Vector2(0, -3),
		"hp": 2,
		"tool": "axe",
		"drop_type": "wood",
		"drop_amount": 2,
		"becomes_stump": false,
	},
	"bush_berry": {
		"texture": "res://assets/objects/bush_berry.png",
		"sprite_offset": Vector2(0, -4),
		"collision_size": Vector2(14, 12),
		"collision_offset": Vector2(0, -3),
		"hp": 1,
		"tool": "any",
		"drop_type": "berry",
		"drop_amount": 2,
		"becomes_stump": false,
	},
	"rock_large": {
		"texture": "res://assets/objects/rock_large.png",
		"sprite_offset": Vector2(0, -8),
		"collision_size": Vector2(24, 18),
		"collision_offset": Vector2(0, -5),
		"hp": 4,
		"tool": "pickaxe",
		"drop_type": "stone",
		"drop_amount": 4,
		"becomes_stump": false,
	},
	"rock_small": {
		"texture": "res://assets/objects/rock_small.png",
		"sprite_offset": Vector2(0, -4),
		"collision_size": Vector2(14, 12),
		"collision_offset": Vector2(0, -3),
		"hp": 2,
		"tool": "pickaxe",
		"drop_type": "stone",
		"drop_amount": 2,
		"becomes_stump": false,
	},
	"rock_ore": {
		"texture": "res://assets/objects/rock_ore.png",
		"sprite_offset": Vector2(0, -4),
		"collision_size": Vector2(14, 12),
		"collision_offset": Vector2(0, -3),
		"hp": 3,
		"tool": "pickaxe",
		"drop_type": "stone",
		"drop_amount": 3,
		"becomes_stump": false,
	},
}

@onready var sprite: Sprite2D = $Sprite2D
@onready var collision_shape: CollisionShape2D = $CollisionShape2D

var hp: int = 3
var debug_draw_enabled: bool = false
var _col_size: Vector2 = Vector2(16, 16)
var _col_offset: Vector2 = Vector2(0, -5)


func _ready() -> void:
	setup_object(object_type)


func setup_object(new_type: String) -> void:
	object_type = new_type
	var def: Dictionary = OBJECT_DEFS.get(object_type, OBJECT_DEFS["tree_oak"])
	hp = def["hp"]
	_col_size = def["collision_size"]
	_col_offset = def["collision_offset"]

	if sprite:
		sprite.texture = load(def["texture"])
		sprite.offset = def["sprite_offset"]
		sprite.position = Vector2.ZERO

	if collision_shape:
		var rect_shape := RectangleShape2D.new()
		rect_shape.size = _col_size
		collision_shape.shape = rect_shape
		collision_shape.position = _col_offset
		collision_shape.disabled = false

	queue_redraw()


func apply_tool_hit(tool_id: String) -> bool:
	var def: Dictionary = OBJECT_DEFS.get(object_type, OBJECT_DEFS["tree_oak"])
	var required_tool: String = def["tool"]

	_play_shake()

	if required_tool != "any" and required_tool != tool_id:
		return false

	hp -= 1
	if hp <= 0:
		resource_dropped.emit(def["drop_type"], def["drop_amount"], global_position)
		if def["becomes_stump"]:
			setup_object("tree_stump")
		else:
			queue_free()
	return true


func _play_shake() -> void:
	if not sprite:
		return
	var tw: Tween = create_tween()
	tw.tween_property(sprite, "position", Vector2(2.0, 0.0), 0.04)
	tw.tween_property(sprite, "position", Vector2(-2.0, 0.0), 0.04)
	tw.tween_property(sprite, "position", Vector2(1.0, 0.0), 0.04)
	tw.tween_property(sprite, "position", Vector2.ZERO, 0.04)


func set_debug_draw(enabled: bool) -> void:
	debug_draw_enabled = enabled
	queue_redraw()


func _draw() -> void:
	if not debug_draw_enabled:
		return
	var rect := Rect2(_col_offset - _col_size * 0.5, _col_size)
	draw_rect(rect, Color(1.0, 0.25, 0.25, 0.45), true)
	draw_rect(rect, Color(1.0, 0.45, 0.2, 0.95), false, 1.0)

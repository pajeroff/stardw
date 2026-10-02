extends Node2D

@onready var world: GameWorld = get_parent()


func _draw() -> void:
	if not world or not world.debug_collisions:
		return
	var ts: float = float(GameWorld.TILE_SIZE)
	var half: float = ts * 0.5
	var fill_col := Color(0.1, 0.55, 1.0, 0.28)
	var line_col := Color(0.2, 0.85, 1.0, 0.75)

	for cell in world.water_cells:
		var center: Vector2 = world.ground_layer.map_to_local(cell)
		var rect := Rect2(center - Vector2(half, half), Vector2(ts, ts))
		draw_rect(rect, fill_col, true)
		draw_rect(rect, line_col, false, 0.75)

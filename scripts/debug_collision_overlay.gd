extends Node2D

@onready var world: GameWorld = get_parent()


func _draw() -> void:
	if not world or not world.debug_collisions:
		return
	var hw: float = float(GameWorld.TILE_W) * 0.5
	var hh: float = float(GameWorld.TILE_H) * 0.5
	var fill_col := Color(0.1, 0.55, 1.0, 0.34)
	var line_col := Color(0.2, 0.85, 1.0, 0.90)

	for cell in world.water_cells:
		var c: Vector2 = world.ground_layer.map_to_local(cell)
		var pts := PackedVector2Array([
			c + Vector2(0, -hh),
			c + Vector2(hw, 0),
			c + Vector2(0, hh),
			c + Vector2(-hw, 0),
			c + Vector2(0, -hh),
		])
		draw_colored_polygon(PackedVector2Array([
			c + Vector2(0, -hh),
			c + Vector2(hw, 0),
			c + Vector2(0, hh),
			c + Vector2(-hw, 0),
		]), fill_col)
		draw_polyline(pts, line_col, 1.2)

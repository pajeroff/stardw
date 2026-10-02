extends Node2D
class_name GameWorld

signal world_regenerated(new_seed: int, stats: Dictionary)
signal inventory_updated(inventory: Dictionary)

@export var map_width: int = 56
@export var map_height: int = 56
@export var world_seed: int = 20261002

const TILE_W: int = 64
const TILE_H: int = 32
const CELL_H: int = 40
const WORLD_OBJECT_SCENE: PackedScene = preload("res://scenes/world_object.tscn")

@onready var ground_layer: TileMapLayer = $GroundLayer
@onready var decor_layer: TileMapLayer = $DecorLayer
@onready var water_body: StaticBody2D = $WaterBody
@onready var y_sort_root: Node2D = $YSortRoot
@onready var objects_container: Node2D = $YSortRoot/ObjectsContainer
@onready var player: Player = $YSortRoot/Player
@onready var border_body: StaticBody2D = $MapBorders
@onready var debug_overlay: Node2D = $DebugCollisionOverlay

var tile_set_resource: TileSet
var water_cells: Array[Vector2i] = []
var debug_collisions: bool = false
var _water_anim_timer: float = 0.0
var _water_anim_phase: int = 0

var inventory: Dictionary = {
	"wood": 0,
	"stone": 0,
	"berry": 0,
	"watered": 0,
}


func _ready() -> void:
	_build_tileset_with_collisions()
	ground_layer.tile_set = tile_set_resource
	decor_layer.tile_set = tile_set_resource

	_setup_isometric_map_borders()

	if player:
		player.tool_used.connect(_on_player_tool_used)

	generate_world(world_seed)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("regenerate_world"):
		regenerate_random_world()
	elif event.is_action_pressed("toggle_debug_collisions"):
		toggle_collision_debug()


func _process(delta: float) -> void:
	_water_anim_timer += delta
	if _water_anim_timer >= 0.55:
		_water_anim_timer = 0.0
		_water_anim_phase = (_water_anim_phase + 1) % 4
		_animate_water_tiles()


func regenerate_random_world() -> void:
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	var next_seed: int = rng.randi_range(100000, 999999)
	generate_world(next_seed)


func toggle_collision_debug() -> void:
	debug_collisions = not debug_collisions
	if player:
		player.set_debug_draw(debug_collisions)
	for child in objects_container.get_children():
		if child.has_method("set_debug_draw"):
			child.set_debug_draw(debug_collisions)
	if debug_overlay:
		debug_overlay.queue_redraw()


func _build_tileset_with_collisions() -> void:
	tile_set_resource = TileSet.new()
	tile_set_resource.tile_shape = TileSet.TILE_SHAPE_ISOMETRIC
	tile_set_resource.tile_layout = TileSet.TILE_LAYOUT_DIAMOND_DOWN
	tile_set_resource.tile_size = Vector2i(TILE_W, TILE_H)

	# Physics Layer 0: Isometric Water & Impassable Terrain (Collision Layer 1)
	tile_set_resource.add_physics_layer()
	tile_set_resource.set_physics_layer_collision_layer(0, 1)
	tile_set_resource.set_physics_layer_collision_mask(0, 0)

	var atlas_tex: Texture2D = load("res://assets/tilesets/world_tileset.png")
	var source := TileSetAtlasSource.new()
	source.texture = atlas_tex
	source.texture_region_size = Vector2i(TILE_W, CELL_H)

	# Attach source to TileSet BEFORE creating tiles & adding collision polygons
	tile_set_resource.add_source(source, 0)

	var cols: int = 16
	var rows: int = 5
	var iso_diamond_poly := PackedVector2Array([
		Vector2(0, -TILE_H * 0.5),
		Vector2(TILE_W * 0.5, 0),
		Vector2(0, TILE_H * 0.5),
		Vector2(-TILE_W * 0.5, 0),
	])

	for ry in range(rows):
		for cx in range(cols):
			var coords := Vector2i(cx, ry)
			source.create_tile(coords)
			var tile_data: TileData = source.get_tile_data(coords, 0)
			if tile_data:
				tile_data.texture_origin = Vector2i(0, -4)
				if ry == 0:
					tile_data.add_collision_polygon(0)
					tile_data.set_collision_polygon_points(0, 0, iso_diamond_poly)


func _setup_isometric_map_borders() -> void:
	for child in border_body.get_children():
		child.queue_free()

	var x_min: int = -map_width / 2
	var x_max: int = map_width / 2 - 1
	var y_min: int = -map_height / 2
	var y_max: int = map_height / 2 - 1

	var c_top: Vector2 = ground_layer.map_to_local(Vector2i(x_min, y_min)) + Vector2(0, -TILE_H)
	var c_right: Vector2 = ground_layer.map_to_local(Vector2i(x_max, y_min)) + Vector2(TILE_W, 0)
	var c_bottom: Vector2 = ground_layer.map_to_local(Vector2i(x_max, y_max)) + Vector2(0, TILE_H)
	var c_left: Vector2 = ground_layer.map_to_local(Vector2i(x_min, y_max)) + Vector2(-TILE_W, 0)

	var corners: Array[Vector2] = [c_top, c_right, c_bottom, c_left]
	for i in range(4):
		var p0: Vector2 = corners[i]
		var p1: Vector2 = corners[(i + 1) % 4]
		var dir: Vector2 = (p1 - p0).normalized()
		var normal: Vector2 = Vector2(dir.y, -dir.x) * 48.0
		var poly := CollisionPolygon2D.new()
		poly.polygon = PackedVector2Array([p0, p1, p1 + normal, p0 + normal])
		border_body.add_child(poly)


func _rebuild_water_physics_bodies() -> void:
	for child in water_body.get_children():
		child.queue_free()

	var iso_diamond := PackedVector2Array([
		Vector2(0, -TILE_H * 0.5),
		Vector2(TILE_W * 0.5, 0),
		Vector2(0, TILE_H * 0.5),
		Vector2(-TILE_W * 0.5, 0),
	])

	for cell in water_cells:
		var poly_node := CollisionPolygon2D.new()
		poly_node.polygon = iso_diamond
		poly_node.position = ground_layer.map_to_local(cell)
		water_body.add_child(poly_node)


func _get_river_center_x(ty: int, base_x: float, bridge_ys: Array[int], river_noise: FastNoiseLite, phase: float) -> float:
	var raw_offset: float = sin(float(ty) * 0.13 + phase) * 3.5 + river_noise.get_noise_1d(float(ty)) * 3.0
	for by in bridge_ys:
		var dist_y: float = absf(float(ty) - (float(by) + 0.5))
		if dist_y < 4.5:
			var target_offset: float = roundf(sin(float(by) * 0.13 + phase) * 3.5 + river_noise.get_noise_1d(float(by)) * 3.0)
			var t: float = clampf(dist_y / 4.5, 0.0, 1.0)
			var smooth_t: float = t * t * (3.0 - 2.0 * t)
			raw_offset = lerpf(target_offset, raw_offset, smooth_t)
	return base_x + raw_offset


func generate_world(new_seed: int) -> void:
	world_seed = new_seed
	ground_layer.clear()
	decor_layer.clear()
	water_cells.clear()

	for child in objects_container.get_children():
		child.queue_free()

	var rng := RandomNumberGenerator.new()
	rng.seed = world_seed

	var elev_noise := FastNoiseLite.new()
	elev_noise.seed = world_seed
	elev_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	elev_noise.frequency = 0.045
	elev_noise.fractal_octaves = 3

	var river_noise := FastNoiseLite.new()
	river_noise.seed = world_seed + 1013
	river_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	river_noise.frequency = 0.032
	river_noise.fractal_octaves = 2

	var forest_noise := FastNoiseLite.new()
	forest_noise.seed = world_seed + 4099
	forest_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	forest_noise.frequency = 0.065
	forest_noise.fractal_octaves = 2

	var x_min: int = -map_width / 2
	var x_max: int = map_width / 2
	var y_min: int = -map_height / 2
	var y_max: int = map_height / 2

	var river_base_x: float = 9.0 if (world_seed % 2 == 0) else 8.0
	var river_phase: float = rng.randf_range(0.0, TAU)
	var river_half_width: float = 1.6
	var bridge_ys: Array[int] = [-13, 0, 13]

	var lake_1_center := Vector2(-14.0 + rng.randf_range(-1.5, 1.5), -10.0 + rng.randf_range(-1.5, 1.5))
	var lake_1_radius: float = 6.2
	var lake_2_center := Vector2(-13.0 + rng.randf_range(-1.5, 1.5), 11.0 + rng.randf_range(-1.5, 1.5))
	var lake_2_radius: float = 5.6

	var water_lookup: Dictionary = {}
	var bridge_lookup: Dictionary = {}
	var path_lookup: Dictionary = {}
	var sand_lookup: Dictionary = {}

	var tree_count: int = 0
	var rock_count: int = 0
	var water_count: int = 0

	var bridge_spans: Array[Dictionary] = []
	for by in bridge_ys:
		var rcx: int = int(roundf(_get_river_center_x(by, river_base_x, bridge_ys, river_noise, river_phase)))
		var bx_start: int = rcx - 2
		var bx_end: int = rcx + 2
		bridge_spans.append({"by": by, "x0": bx_start, "x1": bx_end, "rcx": rcx})
		for ty in range(by, by + 2):
			for tx in range(bx_start, bx_end + 1):
				bridge_lookup[Vector2i(tx, ty)] = true

	for span in bridge_spans:
		var by: int = span["by"]
		var bx0: int = span["x0"]
		var bx1: int = span["x1"]
		for tx in range(-1, bx0):
			path_lookup[Vector2i(tx, by)] = true
			path_lookup[Vector2i(tx, by + 1)] = true
		for tx in range(bx1 + 1, bx1 + 6):
			path_lookup[Vector2i(tx, by)] = true
			path_lookup[Vector2i(tx, by + 1)] = true

	for ty in range(bridge_ys[0], bridge_ys[2] + 2):
		path_lookup[Vector2i(-1, ty)] = true
		path_lookup[Vector2i(0, ty)] = true

	for py in range(-2, 3):
		for px in range(-2, 3):
			if Vector2(px, py).length() <= 2.4:
				path_lookup[Vector2i(px, py)] = true

	# Pass 1: Place Isometric Ground, Lakes, River, Bridges, and Cobblestone Roads
	for ty in range(y_min, y_max):
		var rcx: float = _get_river_center_x(ty, river_base_x, bridge_ys, river_noise, river_phase)
		for tx in range(x_min, x_max):
			var cell := Vector2i(tx, ty)
			var variant: int = posmod(tx * 7 + ty * 13, 4)

			if bridge_lookup.has(cell):
				ground_layer.set_cell(cell, 0, Vector2i(variant % 4, 2))
				continue

			var elev: float = elev_noise.get_noise_2d(float(tx), float(ty))
			var f_val: float = forest_noise.get_noise_2d(float(tx), float(ty))

			var river_dist: float = absf(float(tx) - rcx)
			var is_river: bool = river_dist <= river_half_width

			var l1_dist: float = (Vector2(tx, ty) - lake_1_center).length() + elev * 1.8
			var l2_dist: float = (Vector2(tx, ty) - lake_2_center).length() + elev * 1.8
			var is_lake_1: bool = l1_dist < lake_1_radius
			var is_lake_2: bool = l2_dist < lake_2_radius
			var is_deep_lake: bool = (l1_dist < lake_1_radius * 0.55) or (l2_dist < lake_2_radius * 0.55)
			var is_lake: bool = is_lake_1 or is_lake_2

			if is_river or is_lake:
				var water_col: int = variant
				if is_deep_lake:
					water_col = variant
				elif is_river:
					water_col = 8 + variant
				else:
					water_col = (12 + variant) if rng.randf() < 0.18 else (4 + variant)

				ground_layer.set_cell(cell, 0, Vector2i(water_col, 0))
				water_cells.append(cell)
				water_lookup[cell] = water_col
				water_count += 1
				continue

			# Diverse Land Biomes (Cobblestone Road, Sand Shore, Slate Highland, Sandstone Canyon, Cherry Blossom Lawn, Autumn Maple/Birch Grove, Dark Forest Moss, Meadow)
			if path_lookup.has(cell):
				ground_layer.set_cell(cell, 0, Vector2i(12 + variant, 1))
			elif river_dist <= river_half_width + 1.3 or l1_dist < lake_1_radius + 1.5 or l2_dist < lake_2_radius + 1.5:
				ground_layer.set_cell(cell, 0, Vector2i(variant, 1))
				sand_lookup[cell] = true
			elif ty < -9 and elev > 0.14:
				# Slate rocky highland or warm sandstone plateau
				if tx < 0:
					ground_layer.set_cell(cell, 0, Vector2i(8 + variant, 2))
				else:
					ground_layer.set_cell(cell, 0, Vector2i(4 + variant, 4))
			elif ty > 7 and tx < int(river_base_x) - 2 and f_val > -0.05:
				# Cherry blossom spring lawn (row 4, cols 0..3)
				ground_layer.set_cell(cell, 0, Vector2i(variant, 4))
			elif tx > int(river_base_x) + 3 and f_val > -0.02:
				# Golden/crimson autumn maple & birch grove grass (row 2, cols 12..15)
				ground_layer.set_cell(cell, 0, Vector2i(12 + variant, 2))
			elif f_val > 0.08 or elev > 0.18:
				# Dark emerald forest moss floor (row 1, cols 8..11)
				ground_layer.set_cell(cell, 0, Vector2i(8 + variant, 1))
			elif f_val < -0.15:
				# Lush clover meadow (row 4, cols 8..11)
				ground_layer.set_cell(cell, 0, Vector2i(8 + variant, 4))
			else:
				# Sunlit meadow grass (row 1, cols 4..7)
				ground_layer.set_cell(cell, 0, Vector2i(4 + variant, 1))

	_rebuild_water_physics_bodies()

	# Pass 2: Place All 17 Smooth World Object Varieties (7 Trees, 7 Rocks, 3 Props)
	var occupied_cells: Dictionary = {}

	for ty in range(y_min + 3, y_max - 3):
		for tx in range(x_min + 3, x_max - 3):
			var cell := Vector2i(tx, ty)

			if water_lookup.has(cell) or bridge_lookup.has(cell) or path_lookup.has(cell):
				continue

			if Vector2(tx, ty).length() < 4.2:
				continue

			# Never place on immediate water edge (1 tile buffer) or within 3 tiles of bridges or 1 tile of roads
			if _has_neighbor_in_dict(water_lookup, cell, 1):
				continue
			if _has_neighbor_in_dict(bridge_lookup, cell, 3):
				continue
			if _has_neighbor_in_dict(path_lookup, cell, 1):
				continue

			var near_water_ring: bool = _has_neighbor_in_dict(water_lookup, cell, 3)
			var elev: float = elev_noise.get_noise_2d(float(tx), float(ty))
			var f_val: float = forest_noise.get_noise_2d(float(tx), float(ty))
			var roll: float = rng.randf()

			if not _has_neighbor_in_dict(occupied_cells, cell, 2):
				# Weeping Willows & Mossy River Rocks near riverbanks & lake shores!
				if near_water_ring and roll < 0.25:
					if roll < 0.17:
						_spawn_world_object("tree_willow", cell)
						tree_count += 1
					else:
						_spawn_world_object("rock_river", cell)
						rock_count += 1
					occupied_cells[cell] = true
					continue
				elif not sand_lookup.has(cell) and f_val > 0.03 and roll < 0.36:
					var tree_kind: String = "tree_oak"
					if ty < -7 or elev > 0.22:
						tree_kind = "tree_pine" if (tx + ty) % 2 == 0 else "tree_cedar"
					elif tx > int(river_base_x) + 3:
						var m_mod: int = posmod(tx * 3 + ty * 5, 3)
						if m_mod == 0:
							tree_kind = "tree_maple"
						elif m_mod == 1:
							tree_kind = "tree_birch"
						else:
							tree_kind = "tree_oak"
					elif ty > 6:
						tree_kind = "tree_cherry" if (tx + ty) % 2 == 0 else "tree_oak"
					else:
						var f_mod: int = posmod(tx + ty * 2, 4)
						if f_mod == 0:
							tree_kind = "tree_cedar"
						elif f_mod == 1:
							tree_kind = "tree_cherry"
						else:
							tree_kind = "tree_oak"
					_spawn_world_object(tree_kind, cell)
					occupied_cells[cell] = true
					tree_count += 1
					continue
				elif not sand_lookup.has(cell) and f_val > -0.05 and roll < 0.06:
					var prop_kind: String = "bush_berry" if rng.randf() < 0.65 else ("log_fallen" if rng.randf() < 0.7 else "tree_stump")
					_spawn_world_object(prop_kind, cell)
					occupied_cells[cell] = true
					tree_count += 1
					continue
				elif (elev > 0.08 or ty < -7 or tx > int(river_base_x) + 4) and roll > 0.88:
					var r_roll: float = rng.randf()
					var rock_kind: String = "rock_small"
					if r_roll < 0.18:
						rock_kind = "rock_crystal"
					elif r_roll < 0.36:
						rock_kind = "rock_ore"
					elif r_roll < 0.54:
						rock_kind = "rock_sandstone" if tx > 0 else "rock_slate"
					elif r_roll < 0.72:
						rock_kind = "rock_river"
					elif r_roll < 0.88:
						rock_kind = "rock_large"
					_spawn_world_object(rock_kind, cell)
					occupied_cells[cell] = true
					rock_count += 1
					continue

			if not occupied_cells.has(cell) and rng.randf() < 0.14:
				var d_var: int = rng.randi_range(0, 3)
				if sand_lookup.has(cell):
					decor_layer.set_cell(cell, 0, Vector2i(12 + d_var, 3))
				elif f_val > 0.16:
					var d_col: int = (8 + d_var) if rng.randf() < 0.45 else (4 + d_var)
					decor_layer.set_cell(cell, 0, Vector2i(d_col, 3))
				else:
					var d_col: int = d_var if rng.randf() < 0.55 else (4 + d_var)
					decor_layer.set_cell(cell, 0, Vector2i(d_col, 3))

	if player:
		player.global_position = ground_layer.map_to_local(Vector2i.ZERO)
		player.velocity = Vector2.ZERO

	if debug_overlay:
		debug_overlay.queue_redraw()

	world_regenerated.emit(world_seed, {
		"trees": tree_count,
		"rocks": rock_count,
		"water_tiles": water_count,
		"bridges": bridge_spans.size(),
	})


func _has_neighbor_in_dict(dict: Dictionary, cell: Vector2i, radius: int) -> bool:
	for dy in range(-radius, radius + 1):
		for dx in range(-radius, radius + 1):
			if dict.has(Vector2i(cell.x + dx, cell.y + dy)):
				return true
	return false


func _spawn_world_object(kind: String, cell: Vector2i) -> void:
	var obj: WorldObject = WORLD_OBJECT_SCENE.instantiate()
	obj.object_type = kind
	obj.position = ground_layer.map_to_local(cell)
	obj.debug_draw_enabled = debug_collisions
	obj.resource_dropped.connect(_on_object_resource_dropped)
	objects_container.add_child(obj)


func _on_player_tool_used(tool_id: String, target_global_pos: Vector2, _facing_dir: Vector2) -> void:
	var closest_obj: WorldObject = null
	var best_dist: float = 52.0

	for child in objects_container.get_children():
		if child is WorldObject:
			var obj_center: Vector2 = child.global_position + Vector2(0, -8)
			var d: float = obj_center.distance_to(target_global_pos)
			if d < best_dist:
				best_dist = d
				closest_obj = child

	if closest_obj != null:
		closest_obj.apply_tool_hit(tool_id)
		return

	if tool_id == "water":
		var local_pos: Vector2 = ground_layer.to_local(target_global_pos)
		var cell: Vector2i = ground_layer.local_to_map(local_pos)
		var atlas_coords: Vector2i = ground_layer.get_cell_atlas_coords(cell)
		if atlas_coords.y == 1 or (atlas_coords.y == 2 and atlas_coords.x >= 8) or atlas_coords.y == 4:
			var variant: int = posmod(cell.x + cell.y, 4)
			ground_layer.set_cell(cell, 0, Vector2i(4 + variant, 2))
			if decor_layer.get_cell_source_id(cell) == -1:
				decor_layer.set_cell(cell, 0, Vector2i(variant, 3))
			inventory["watered"] += 1
			inventory_updated.emit(inventory)


func _on_object_resource_dropped(resource_type: String, amount: int, _world_pos: Vector2) -> void:
	if inventory.has(resource_type):
		inventory[resource_type] += amount
		inventory_updated.emit(inventory)


func _animate_water_tiles() -> void:
	for cell in water_cells:
		var coords: Vector2i = ground_layer.get_cell_atlas_coords(cell)
		if coords.y == 0 and coords.x < 12:
			var group_base: int = (coords.x / 4) * 4
			var next_col: int = group_base + ((coords.x + 1) % 4)
			ground_layer.set_cell(cell, 0, Vector2i(next_col, 0))

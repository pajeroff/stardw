extends Node2D
class_name GameWorld

signal world_regenerated(new_seed: int, stats: Dictionary)
signal inventory_updated(inventory: Dictionary)

@export var map_width: int = 88
@export var map_height: int = 68
@export var world_seed: int = 20261002

const TILE_SIZE: int = 16
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
var bridge_rail_rects: Array[Rect2] = []
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

	_setup_map_borders()

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
	tile_set_resource.tile_size = Vector2i(TILE_SIZE, TILE_SIZE)

	# Physics Layer 0: Water & Impassable Terrain (Collision Layer 1)
	tile_set_resource.add_physics_layer()
	tile_set_resource.set_physics_layer_collision_layer(0, 1)
	tile_set_resource.set_physics_layer_collision_mask(0, 0)

	var atlas_tex: Texture2D = load("res://assets/tilesets/world_tileset.png")
	var source := TileSetAtlasSource.new()
	source.texture = atlas_tex
	source.texture_region_size = Vector2i(TILE_SIZE, TILE_SIZE)

	# IMPORTANT: Attach source to TileSet BEFORE creating tiles & adding collision polygons
	# so TileData knows physics_layer 0 exists!
	tile_set_resource.add_source(source, 0)

	var cols: int = 16
	var rows: int = 5
	var full_tile_poly := PackedVector2Array([
		Vector2(-8, -8),
		Vector2(8, -8),
		Vector2(8, 8),
		Vector2(-8, 8),
	])

	for ry in range(rows):
		for cx in range(cols):
			var coords := Vector2i(cx, ry)
			source.create_tile(coords)
			var tile_data: TileData = source.get_tile_data(coords, 0)
			# Row 0 contains all water tiles (Deep lake, Shallow lake, River, Lilypads)
			if ry == 0 and tile_data:
				tile_data.add_collision_polygon(0)
				tile_data.set_collision_polygon_points(0, 0, full_tile_poly)


func _setup_map_borders() -> void:
	for child in border_body.get_children():
		child.queue_free()

	var half_w: float = (map_width * TILE_SIZE) * 0.5
	var half_h: float = (map_height * TILE_SIZE) * 0.5
	var thickness: float = 32.0

	var walls: Array[Dictionary] = [
		{"pos": Vector2(0, -half_h - thickness * 0.5), "size": Vector2(half_w * 2.0 + 64.0, thickness)},
		{"pos": Vector2(0, half_h + thickness * 0.5),  "size": Vector2(half_w * 2.0 + 64.0, thickness)},
		{"pos": Vector2(-half_w - thickness * 0.5, 0), "size": Vector2(thickness, half_h * 2.0 + 64.0)},
		{"pos": Vector2(half_w + thickness * 0.5, 0),  "size": Vector2(thickness, half_h * 2.0 + 64.0)},
	]

	for w in walls:
		var shape_node := CollisionShape2D.new()
		var rect := RectangleShape2D.new()
		rect.size = w["size"]
		shape_node.shape = rect
		shape_node.position = w["pos"]
		border_body.add_child(shape_node)


func _rebuild_water_physics_bodies(water_lookup: Dictionary) -> void:
	for child in water_body.get_children():
		child.queue_free()

	var x_min: int = -map_width / 2
	var x_max: int = map_width / 2
	var y_min: int = -map_height / 2
	var y_max: int = map_height / 2

	# Merge contiguous horizontal water cells into clean RectangleShape2D strips
	for ty in range(y_min, y_max):
		var run_start: int = -999999
		var run_len: int = 0
		for tx in range(x_min, x_max + 1):
			var is_w: bool = (tx < x_max) and water_lookup.has(Vector2i(tx, ty))
			if is_w:
				if run_len == 0:
					run_start = tx
				run_len += 1
			else:
				if run_len > 0:
					var rect_shape := RectangleShape2D.new()
					rect_shape.size = Vector2(float(run_len * TILE_SIZE), float(TILE_SIZE))
					var col_node := CollisionShape2D.new()
					col_node.shape = rect_shape
					var start_local: Vector2 = ground_layer.map_to_local(Vector2i(run_start, ty))
					var center_x: float = start_local.x + float(run_len - 1) * float(TILE_SIZE) * 0.5
					col_node.position = Vector2(center_x, start_local.y)
					water_body.add_child(col_node)
					run_len = 0

	# Also add thin top & bottom guardrails along bridges so player stays safely on the bridge deck
	for rail_rect in bridge_rail_rects:
		var r_shape := RectangleShape2D.new()
		r_shape.size = rail_rect.size
		var c_node := CollisionShape2D.new()
		c_node.shape = r_shape
		c_node.position = rail_rect.position + rail_rect.size * 0.5
		water_body.add_child(c_node)


func _get_river_center_x(ty: int, base_x: float, bridge_ys: Array[int], river_noise: FastNoiseLite, phase: float) -> float:
	var raw_offset: float = sin(float(ty) * 0.11 + phase) * 4.5 + river_noise.get_noise_1d(float(ty)) * 4.0
	# Flatten river curvature smoothly near bridge crossings so bridges sit perpendicular to straight banks
	for by in bridge_ys:
		var dist_y: float = absf(float(ty) - (float(by) + 0.5))
		if dist_y < 5.0:
			var target_offset: float = roundf(sin(float(by) * 0.11 + phase) * 4.5 + river_noise.get_noise_1d(float(by)) * 4.0)
			var t: float = clampf(dist_y / 5.0, 0.0, 1.0)
			var smooth_t: float = t * t * (3.0 - 2.0 * t)
			raw_offset = lerpf(target_offset, raw_offset, smooth_t)
	return base_x + raw_offset


func generate_world(new_seed: int) -> void:
	world_seed = new_seed
	ground_layer.clear()
	decor_layer.clear()
	water_cells.clear()
	bridge_rail_rects.clear()

	for child in objects_container.get_children():
		child.queue_free()

	var rng := RandomNumberGenerator.new()
	rng.seed = world_seed

	var elev_noise := FastNoiseLite.new()
	elev_noise.seed = world_seed
	elev_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	elev_noise.frequency = 0.035
	elev_noise.fractal_octaves = 3

	var river_noise := FastNoiseLite.new()
	river_noise.seed = world_seed + 1013
	river_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	river_noise.frequency = 0.025
	river_noise.fractal_octaves = 2

	var forest_noise := FastNoiseLite.new()
	forest_noise.seed = world_seed + 4099
	forest_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	forest_noise.frequency = 0.052
	forest_noise.fractal_octaves = 2

	var x_min: int = -map_width / 2
	var x_max: int = map_width / 2
	var y_min: int = -map_height / 2
	var y_max: int = map_height / 2

	# 1. River layout: flows North-to-South on the East side of spawn (x ~ +13)
	var river_base_x: float = 13.0 if (world_seed % 2 == 0) else 11.0
	var river_phase: float = rng.randf_range(0.0, TAU)
	var river_half_width: float = 2.0
	var bridge_ys: Array[int] = [-18, 0, 18]

	# 2. Scenic Lakes (placed in West quadrants, away from river, roads, and spawn)
	var lake_1_center := Vector2(-24.0 + rng.randf_range(-2.0, 2.0), -14.0 + rng.randf_range(-2.0, 2.0))
	var lake_1_radius: float = 8.2
	var lake_2_center := Vector2(-22.0 + rng.randf_range(-2.0, 2.0), 15.0 + rng.randf_range(-2.0, 2.0))
	var lake_2_radius: float = 7.2

	var water_lookup: Dictionary = {}
	var bridge_lookup: Dictionary = {}
	var path_lookup: Dictionary = {}
	var sand_lookup: Dictionary = {}

	var tree_count: int = 0
	var rock_count: int = 0
	var water_count: int = 0
	var bridge_count: int = 0

	# Precompute straight wooden bridges across the 3 river crossings
	var bridge_spans: Array[Dictionary] = []
	for by in bridge_ys:
		var rcx: int = int(roundf(_get_river_center_x(by, river_base_x, bridge_ys, river_noise, river_phase)))
		var bx_start: int = rcx - 3  # 1 full tile onto West dry bank
		var bx_end: int = rcx + 3    # 1 full tile onto East dry bank
		bridge_spans.append({"by": by, "x0": bx_start, "x1": bx_end, "rcx": rcx})
		for ty in range(by, by + 2):
			for tx in range(bx_start, bx_end + 1):
				bridge_lookup[Vector2i(tx, ty)] = true

		# Add thin top & bottom guardrail collision rects over the water portion of the bridge
		var water_x0: float = float(rcx - 2) * float(TILE_SIZE)
		var water_w: float = 5.0 * float(TILE_SIZE)
		var top_y: float = float(by) * float(TILE_SIZE)
		var bot_y: float = float(by + 2) * float(TILE_SIZE) - 2.0
		bridge_rail_rects.append(Rect2(Vector2(water_x0, top_y), Vector2(water_w, 2.0)))
		bridge_rail_rects.append(Rect2(Vector2(water_x0, bot_y), Vector2(water_w, 2.0)))

	# Precompute clean 2-tile-wide dirt trails connecting spawn (0,0) and all 3 bridges
	for span in bridge_spans:
		var by: int = span["by"]
		var bx0: int = span["x0"]
		var bx1: int = span["x1"]
		# Horizontal road from West trunk road (x = -1..0) to West bridge entrance (bx0 - 1)
		for tx in range(-1, bx0):
			path_lookup[Vector2i(tx, by)] = true
			path_lookup[Vector2i(tx, by + 1)] = true
		# Horizontal road from East bridge exit (bx1 + 1) to East forest road (bx1 + 6)
		for tx in range(bx1 + 1, bx1 + 7):
			path_lookup[Vector2i(tx, by)] = true
			path_lookup[Vector2i(tx, by + 1)] = true

	# Vertical West trunk road connecting North bridge (-18) through Spawn (0) to South bridge (+18)
	for ty in range(bridge_ys[0], bridge_ys[2] + 2):
		path_lookup[Vector2i(-1, ty)] = true
		path_lookup[Vector2i(0, ty)] = true

	# Small cozy cobblestone/dirt plaza at Spawn (0,0)
	for py in range(-2, 3):
		for px in range(-2, 3):
			if Vector2(px, py).length() <= 2.4:
				path_lookup[Vector2i(px, py)] = true

	# Pass 1: Place Ground, Lakes, River, Bridges, and Roads
	for ty in range(y_min, y_max):
		var rcx: float = _get_river_center_x(ty, river_base_x, bridge_ys, river_noise, river_phase)
		for tx in range(x_min, x_max):
			var cell := Vector2i(tx, ty)
			var variant: int = posmod(tx * 7 + ty * 13, 4)

			# If this cell is part of a precomputed wooden bridge:
			if bridge_lookup.has(cell):
				ground_layer.set_cell(cell, 0, Vector2i(variant % 2, 2))
				bridge_count += 1
				continue

			var elev: float = elev_noise.get_noise_2d(float(tx), float(ty))
			var f_val: float = forest_noise.get_noise_2d(float(tx), float(ty))

			# Distance to River centerline
			var river_dist: float = absf(float(tx) - rcx)
			var is_river: bool = river_dist <= river_half_width

			# Distance to Scenic Lakes (perturbed organically by elevation noise)
			var l1_dist: float = (Vector2(tx, ty) - lake_1_center).length() + elev * 2.4
			var l2_dist: float = (Vector2(tx, ty) - lake_2_center).length() + elev * 2.2
			var is_lake_1: bool = l1_dist < lake_1_radius
			var is_lake_2: bool = l2_dist < lake_2_radius
			var is_deep_lake: bool = (l1_dist < lake_1_radius * 0.56) or (l2_dist < lake_2_radius * 0.56)
			var is_lake: bool = is_lake_1 or is_lake_2

			if is_river or is_lake:
				var water_col: int = variant
				if is_deep_lake:
					water_col = variant  # Cols 0..3: Deep Lake Water
				elif is_river:
					water_col = 8 + variant  # Cols 8..11: Flowing River Water
				else:
					# Shallow lake rim with occasional lilypads
					if rng.randf() < 0.16:
						water_col = 12 + variant  # Cols 12..15: Lilypads
					else:
						water_col = 4 + variant   # Cols 4..7: Shallow Water

				ground_layer.set_cell(cell, 0, Vector2i(water_col, 0))
				water_cells.append(cell)
				water_lookup[cell] = water_col
				water_count += 1
				continue

			# Dry Land Tiles
			if path_lookup.has(cell):
				ground_layer.set_cell(cell, 0, Vector2i(12 + variant, 1))
			elif river_dist <= river_half_width + 1.4 or l1_dist < lake_1_radius + 1.8 or l2_dist < lake_2_radius + 1.8:
				# Natural sandy beach / riverbank
				ground_layer.set_cell(cell, 0, Vector2i(variant, 1))
				sand_lookup[cell] = true
			elif f_val > 0.08 or elev > 0.20:
				# Rich dark forest moss grass
				ground_layer.set_cell(cell, 0, Vector2i(8 + variant, 1))
			else:
				# Lush meadow grass
				ground_layer.set_cell(cell, 0, Vector2i(4 + variant, 1))

	# Build solid physics collision shapes for all water tiles & bridge rails
	_rebuild_water_physics_bodies(water_lookup)

	# Pass 2: Place Forest Trees, Rocks, Berry Bushes, Logs & Decor with Strict Buffer Zones
	var occupied_cells: Dictionary = {}

	for ty in range(y_min + 3, y_max - 3):
		for tx in range(x_min + 3, x_max - 3):
			var cell := Vector2i(tx, ty)

			# Never place on water, bridges, roads, or sand beaches
			if water_lookup.has(cell) or bridge_lookup.has(cell) or path_lookup.has(cell) or sand_lookup.has(cell):
				continue

			# Keep spawn area around (0, 0) open
			if Vector2(tx, ty).length() < 5.0:
				continue

			# Keep 2-tile clearance from water, 3-tile clearance from bridges, 1-tile clearance from roads
			if _has_neighbor_in_dict(water_lookup, cell, 2):
				continue
			if _has_neighbor_in_dict(bridge_lookup, cell, 3):
				continue
			if _has_neighbor_in_dict(path_lookup, cell, 1):
				continue

			var elev: float = elev_noise.get_noise_2d(float(tx), float(ty))
			var f_val: float = forest_noise.get_noise_2d(float(tx), float(ty))
			var roll: float = rng.randf()

			# Check 2-tile spacing between solid objects so trees/rocks never overlap or jam together
			if not _has_neighbor_in_dict(occupied_cells, cell, 2):
				# Forest Groves (clustered by biome region)
				if f_val > 0.06 and roll < 0.34:
					var tree_kind: String = "tree_oak"
					if ty < -8 or elev > 0.26:
						tree_kind = "tree_pine"
					elif tx > int(river_base_x) + 3:
						tree_kind = "tree_birch" if (tx + ty) % 2 == 0 else "tree_oak"
					_spawn_world_object(tree_kind, cell)
					occupied_cells[cell] = true
					tree_count += 1
					continue
				elif f_val > -0.05 and roll < 0.05:
					var bush_or_log: String = "bush_berry" if rng.randf() < 0.72 else "log_fallen"
					_spawn_world_object(bush_or_log, cell)
					occupied_cells[cell] = true
					tree_count += 1
					continue
				elif (elev > 0.14 or tx > int(river_base_x) + 6) and roll > 0.93:
					var rock_kind: String = "rock_large" if rng.randf() < 0.32 else ("rock_ore" if rng.randf() < 0.45 else "rock_small")
					_spawn_world_object(rock_kind, cell)
					occupied_cells[cell] = true
					rock_count += 1
					continue

			# Non-colliding ground decor (wildflowers, tall grass, mushrooms, pebbles)
			if not occupied_cells.has(cell) and rng.randf() < 0.13:
				var d_var: int = rng.randi_range(0, 3)
				if f_val > 0.16:
					var d_col: int = (8 + d_var) if rng.randf() < 0.42 else (4 + d_var)
					decor_layer.set_cell(cell, 0, Vector2i(d_col, 3))
				else:
					var d_col: int = d_var if rng.randf() < 0.55 else (4 + d_var)
					decor_layer.set_cell(cell, 0, Vector2i(d_col, 3))

	# Reset player to safe center spawn
	if player:
		player.global_position = Vector2.ZERO
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
	var best_dist: float = 22.0

	for child in objects_container.get_children():
		if child is WorldObject:
			var obj_center: Vector2 = child.global_position + Vector2(0, -5)
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
		if atlas_coords.y == 1:
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

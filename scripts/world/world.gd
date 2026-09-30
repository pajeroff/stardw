extends Node2D
## World: builds the isometric island from MapGen -- terrain TileMapLayer,
## props, buildings, water sparkles -- and answers spatial queries.

signal season_applied(season: int)

const MapGenS = preload("res://scripts/world/map_gen.gd")
const IsoS = preload("res://scripts/world/iso.gd")

var map = null                 # MapGen instance
var blocked: Dictionary = {}   # cell -> true
var interactables: Dictionary = {}  # cell -> type
var water_cells_by_type: Dictionary = {}

var tile_layer: TileMapLayer = null
var entities: Node2D = null
var _sparkles: Array = []
var _spark_timer: float = 0.0

func _ready() -> void:
	map = MapGenS.new()
	map.generate(Game.randi_range(1, 99999))
	entities = Node2D.new()
	entities.y_sort_enabled = true
	add_child(entities)
	_build_terrain()
	_build_props()
	_build_buildings()
	_index_water()
	_make_sparkles()
	Game.day_changed.connect(_on_season)

func _on_season(_d, season, _y) -> void:
	_apply_season(season)

# ------------------------------------------------------------- terrain ------
func _build_terrain() -> void:
	var ts := TileSet.new()
	ts.tile_size = Vector2i(64, 32)
	ts.tile_shape = TileSet.TILE_SHAPE_ISOMETRIC
	var src := TileSetAtlasSource.new()
	src.texture = Art.atlas("tiles")
	src.texture_region_size = Vector2i(64, 32)
	var source_id := ts.add_source(src)
	var regions: Dictionary = Art.tile_info()["regions"]
	var name_to_coord := {}
	for nm in regions:
		var r = regions[nm]
		var coord := Vector2i(r[0] / 64, r[1] / 32)
		name_to_coord[nm] = coord
		if not src.has_tile(coord):
			src.create_tile(coord)
	tile_layer = TileMapLayer.new()
	tile_layer.tile_set = ts
	add_child(tile_layer)
	for c in map.grid:
		tile_layer.set_cell(c, source_id, name_to_coord[map.grid[c]])
		if map.is_water(c):
			blocked[c] = true

# ---------------------------------------------------------------- props -----
func _tree_for(season: int, big: bool) -> String:
	match season:
		0: return "tree_blossom" if big else "tree_oak_small"
		1: return "tree_oak_big" if big else "tree_oak"
		2: return "tree_autumn" if big else "tree_pine"
		_: return "tree_pine_snow" if big else "tree_bare"

func _build_props() -> void:
	for p in map.props:
		var cell: Vector2i = p["cell"]
		var t: String = p["type"]
		var name := ""
		var solid := false
		match t:
			"tree":
				name = _tree_for(Game.season, Game.randf() < 0.4)
				solid = true
			"rock":
				name = ["rock_small", "rock_big", "rock_mossy"][Game.randi_range(0, 2)]
				solid = true
			"flower":
				name = ["flower_red", "flower_blue", "flower_yellow"][Game.randi_range(0, 2)]
			"tall_grass":
				name = "tall_grass"
			"reeds":
				name = "reeds" if Game.randf() < 0.5 else "cattail"
		if name == "":
			continue
		_spawn_sprite(name, cell, 0.0)
		if solid:
			blocked[cell] = true
		elif t == "tall_grass":
			pass  # walkable

func _build_buildings() -> void:
	for b in map.buildings:
		var cell: Vector2i = b["cell"]
		match b["type"]:
			"house":
				_spawn_sprite("house", cell, 0.0, Vector2i(3, 2))
				_block(cell, Vector2i(3, 2))
				interactables[cell + Vector2i(1, 2)] = "house"
			"shop":
				_spawn_sprite("shop", cell, 0.0, Vector2i(3, 2))
				_block(cell, Vector2i(3, 2))
				interactables[cell + Vector2i(1, 2)] = "shop"
			"board":
				_spawn_sprite("quest_board", cell, 0.0)
				interactables[cell + Vector2i(0, 1)] = "board"
				blocked[cell] = true
			"well":
				_spawn_sprite("well", cell, 0.0)
				interactables[cell + Vector2i(0, 1)] = "well"
				blocked[cell] = true
			"campfire":
				_spawn_campfire(cell)
				interactables[cell + Vector2i(0, 1)] = "campfire"
				blocked[cell] = true
			"boat":
				_spawn_sprite("boat", cell, 0.0)
			"pier_post":
				_spawn_sprite("pier_post", cell, 0.0)

func _spawn_sprite(name: String, cell: Vector2i, lift: float = 0.0, footprint: Vector2i = Vector2i(1, 1)) -> Sprite2D:
	var sp := Sprite2D.new()
	sp.texture = Art.tex(name)
	sp.centered = false
	var w := Art.region_rect(name).size.x
	var h := Art.region_rect(name).size.y
	var l := IsoS.cell_to_local(cell)
	sp.position = Vector2(l.x - w * 0.5, l.y + 24.0 - h - lift)
	sp.add_to_group("prop")
	entities.add_child(sp)
	return sp

func _block(cell: Vector2i, footprint: Vector2i) -> void:
	for dx in footprint.x:
		for dy in footprint.y:
			blocked[cell + Vector2i(dx, dy)] = true

func _spawn_campfire(cell: Vector2i) -> void:
	var fr = Art.frames("campfire")
	var sp := Sprite2D.new()
	sp.centered = false
	var w := Art.region_rect("campfire_0").size.x
	var h := Art.region_rect("campfire_0").size.y
	var l := IsoS.cell_to_local(cell)
	sp.position = Vector2(l.x - w * 0.5, l.y + 24.0 - h)
	sp.texture = fr[0][0]
	sp.add_to_group("prop")
	entities.add_child(sp)
	var timer := Timer.new()
	timer.wait_time = 1.0 / fr[1]
	timer.timeout.connect(func():
		var i := (int(Time.get_ticks_msec() / (1000.0 / fr[1])) % fr[0].size())
		if is_instance_valid(sp):
			sp.texture = fr[0][i])
	sp.add_child(timer)
	timer.start()
	# warm glow
	var glow := Sprite2D.new()
	glow.texture = Art.tex("glow_warm")
	glow.centered = true
	glow.position = l + Vector2(0, -10)
	glow.modulate.a = 0.6
	glow.add_to_group("prop")
	entities.add_child(glow)

# --------------------------------------------------------------- water ------
func _index_water() -> void:
	for c in map.water:
		var t: String = map.water[c]
		if not water_cells_by_type.has(t):
			water_cells_by_type[t] = []
		water_cells_by_type[t].append(c)

func _make_sparkles() -> void:
	for i in 10:
		var sp := Sprite2D.new()
		sp.texture = Art.tex("water_sparkle")
		sp.centered = true
		sp.modulate.a = 0.0
		add_child(sp)
		_sparkles.append({"node": sp, "t": randf() * 4.0, "cell": Vector2i.ZERO})

func _process(delta: float) -> void:
	_spark_timer += delta
	if _spark_timer > 0.6:
		_spark_timer = 0.0
		for s in _sparkles:
			var t = pick_water_cell()
			if t != null:
				s["cell"] = t
				s["t"] = 0.0
				s["node"].position = IsoS.cell_to_local(t)
	for s in _sparkles:
		s["t"] += delta
		var k := s["t"] / 1.2
		s["node"].modulate.a = maxf(0.0, sin(k * PI)) * 0.8

func pick_water_cell(type: String = "") -> Vector2i:
	var pools := water_cells_by_type
	if type != "" and pools.has(type):
		return pools[type][Game.randi_range(0, pools[type].size() - 1)]
	var keys := pools.keys()
	if keys.is_empty():
		return Vector2i.ZERO
	var k = keys[Game.randi_range(0, keys.size() - 1)]
	return pools[k][Game.randi_range(0, pools[k].size() - 1)]

# ------------------------------------------------------------- queries ------
func cell_at(world_pos: Vector2) -> Vector2i:
	return IsoS.local_to_cell(world_pos)

func is_walkable(cell: Vector2i) -> bool:
	if not map.inb(cell):
		return false
	if map.is_water(cell):
		return false
	return not blocked.has(cell)

func water_type_at(cell: Vector2i) -> String:
	return map.water_type(cell)

func interactable_near(cell: Vector2i) -> String:
	if interactables.has(cell):
		return interactables[cell]
	for n in [cell + Vector2i(1, 0), cell + Vector2i(-1, 0), cell + Vector2i(0, 1), cell + Vector2i(0, -1)]:
		if interactables.has(n):
			return interactables[n]
	return ""

func fishing_cell_from(cell: Vector2i, facing: Vector2) -> Vector2i:
	# choose the adjacent water cell closest to the facing direction
	var best: Vector2i = Vector2i.ZERO
	var best_dot := -2.0
	for n in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1),
			  Vector2i(1, 1), Vector2i(-1, -1), Vector2i(1, -1), Vector2i(-1, 1)]:
		var c := cell + n
		if map.is_water(c):
			var dir := Vector2(n.x - n.y, (n.x + n.y) * 0.5).normalized()
			var d := dir.dot(facing.normalized())
			if d > best_dot:
				best_dot = d
				best = c
	return best

func _apply_season(season: int) -> void:
	# recolour trees by swapping tree sprites (rebuild props only, keep player)
	for ch in entities.get_children():
		if ch.is_in_group("prop"):
			ch.queue_free()
	interactables.clear()
	blocked.clear()
	# re-add water blocks
	for c in map.water:
		blocked[c] = true
	_build_props()
	_build_buildings()
	season_applied.emit(season)

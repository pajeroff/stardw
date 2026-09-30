extends Node
## Art: loads the generated manifest.json and hands out AtlasTextures.
## Every visual in the game is drawn by tools/gen_assets.py and referenced here.

var manifest: Dictionary = {}
var _atlas_tex: Dictionary = {}      # atlas name -> Texture2D
var _index: Dictionary = {}          # region name -> [atlas, [x,y,w,h]]
var _tex_cache: Dictionary = {}      # region name -> AtlasTexture

func _ready() -> void:
	var text: String = FileAccess.get_file_as_string("res://assets/manifest.json")
	manifest = JSON.parse_string(text)
	for at in manifest["atlases"]:
		_atlas_tex[at] = load("res://assets/" + manifest["atlases"][at]["file"])
	for at in manifest["atlases"]:
		var regions: Dictionary = manifest["atlases"][at]["regions"]
		for nm in regions:
			_index[nm] = [at, regions[nm]]
	_setup_input()

func has(nm: String) -> bool:
	return _index.has(nm)

func atlas(nm: String) -> Texture2D:
	return _atlas_tex[nm]

func region_rect(nm: String) -> Rect2:
	var e = _index[nm]
	return Rect2(e[1][0], e[1][1], e[1][2], e[1][3])

func tex(nm: String) -> AtlasTexture:
	if _tex_cache.has(nm):
		return _tex_cache[nm]
	var e = _index[nm]
	var at := AtlasTexture.new()
	at.atlas = _atlas_tex[e[0]]
	at.region = Rect2(e[1][0], e[1][1], e[1][2], e[1][3])
	_tex_cache[nm] = at
	return at

## Returns a list of [AtlasTexture, fps] for an animation entry.
func frames(nm: String) -> Array:
	var a: Dictionary = manifest["anims"][nm]
	var atlas: String = a["atlas"]
	var out: Array = []
	for r in a["frames"]:
		var at := AtlasTexture.new()
		at.atlas = _atlas_tex[atlas]
		at.region = Rect2(r[0], r[1], r[2], r[3])
		out.append(at)
	return [out, a["fps"]]

func tile_info() -> Dictionary:
	return manifest["atlases"]["tiles"]

func _setup_input() -> void:
	_add("move_up", [KEY_W, KEY_UP])
	_add("move_down", [KEY_S, KEY_DOWN])
	_add("move_left", [KEY_A, KEY_LEFT])
	_add("move_right", [KEY_D, KEY_RIGHT])
	_add("interact", [KEY_E])
	_add("use", [KEY_SPACE])
	_add("dash", [KEY_SHIFT])
	_add("dex", [KEY_F])
	_add("journal", [KEY_J])
	_add("menu", [KEY_ESCAPE])

func _add(action: StringName, keys: Array) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action, 0.4)
	for k in keys:
		var ev := InputEventKey.new()
		ev.keycode = k
		InputMap.action_add_event(action, ev)

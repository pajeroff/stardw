extends CanvasLayer

@onready var world: GameWorld = $"../World"
@onready var info_label: Label = $TopLeftPanel/MarginContainer/VBoxContainer/InfoLabel
@onready var resources_label: Label = $TopLeftPanel/MarginContainer/VBoxContainer/ResourcesLabel
@onready var hotbar_label: Label = $BottomHotbar/MarginContainer/HotbarLabel
@onready var btn_regen: Button = $TopLeftPanel/MarginContainer/VBoxContainer/ButtonsRow/RegenButton
@onready var btn_debug: Button = $TopLeftPanel/MarginContainer/VBoxContainer/ButtonsRow/DebugButton

var _current_seed: int = 20261002
var _current_anim: String = "idle"
var _current_dir: String = "down"
var _current_tool_idx: int = 0
var _current_tool_title: String = "Топор (Рубка леса)"
var _world_stats: Dictionary = {}


func _ready() -> void:
	if world:
		world.world_regenerated.connect(_on_world_regenerated)
		world.inventory_updated.connect(_on_inventory_updated)
		var player: Player = world.get_node_or_null("YSortRoot/Player")
		if player:
			player.state_changed.connect(_on_player_state_changed)
			player.tool_changed.connect(_on_player_tool_changed)

	if btn_regen:
		btn_regen.pressed.connect(func() -> void:
			if world:
				world.regenerate_random_world()
		)

	if btn_debug:
		btn_debug.pressed.connect(func() -> void:
			if world:
				world.toggle_collision_debug()
				_refresh_labels()
		)

	_refresh_labels()


func _on_world_regenerated(new_seed: int, stats: Dictionary) -> void:
	_current_seed = new_seed
	_world_stats = stats
	_refresh_labels()


func _on_inventory_updated(inv: Dictionary) -> void:
	if resources_label:
		resources_label.text = "Дерево: %d  |  Камень: %d  |  Ягоды: %d  |  Полито: %d" % [
			inv.get("wood", 0),
			inv.get("stone", 0),
			inv.get("berry", 0),
			inv.get("watered", 0),
		]


func _on_player_state_changed(anim_state: String, dir_name: String, _dir_vec: Vector2) -> void:
	_current_anim = anim_state
	_current_dir = dir_name
	_refresh_labels()


func _on_player_tool_changed(tool_index: int, _tool_id: String, tool_title: String) -> void:
	_current_tool_idx = tool_index
	_current_tool_title = tool_title
	_refresh_labels()


func _refresh_labels() -> void:
	if info_label:
		var dir_ru: String = Player.DIRECTION_LABELS_RU.get(_current_dir, _current_dir)
		var col_state: String = "ВКЛ" if (world and world.debug_collisions) else "ВЫКЛ"
		info_label.text = (
			"Сид мира: %d (Лес: %d | Камни: %d | Мосты: %d)\n" % [
				_current_seed,
				_world_stats.get("trees", 0),
				_world_stats.get("rocks", 0),
				_world_stats.get("bridges", 0),
			]
			+ "Анимация: %s_%s  |  Ось (8 напр.): %s\n" % [_current_anim, _current_dir, dir_ru]
			+ "Управление: WASD/Стрелки (Ходьба) | Shift (Бег) | Пробел/ЛКМ (Инструмент) | E (Действие)\n"
			+ "Отображение коллизий [C/F3]: %s  |  Перегенерация мира: [R]" % col_state
		)

	if hotbar_label:
		var slots: Array[String] = [
			"[1] Топор",
			"[2] Кирка",
			"[3] Лейка",
			"[4] Рука",
		]
		for i in range(slots.size()):
			if i == _current_tool_idx:
				slots[i] = ">> " + slots[i] + " <<"
		hotbar_label.text = "   |   ".join(slots) + "     (" + _current_tool_title + ")"

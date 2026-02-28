#!/usr/bin/env python3
"""
Generate skill frame data JSON from game XML configs.

Parses:
- SkillData.xml: Skill definitions (ID, Name, Type, CastActionID, BulletID, etc.)
- SkillPropertiesLua.xml: Skill timing (cooldown, state time, etc.)
- BulletConfig.xml: Projectile timing (LifeTime, DamageInterval, etc.)

Game timing system:
- Tick rate: 18 Hz (1 tick = 1/18 second ≈ 55.6ms)
- skill_mintimepercast_v: Raw value in ticks at 18Hz
- Attack speed (0-100) determines action duration: 0.2s (speed=100) to 0.8s (speed=0)
- MinAttackActionDuration = 0.2s, MaxAttackActionDuration = 0.8s
- AttackSpeedAdditionDuration = 0.1s (gap between consecutive casts)
"""

import xml.etree.ElementTree as ET
import json
import math
import os
import re

TICK_RATE = 18  # Hz
MIN_ATK_DURATION = 0.2  # seconds
MAX_ATK_DURATION = 0.8  # seconds
ATK_SPEED_ADDITION = 0.1  # seconds gap between casts

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "server", "bin", "GameServer", "Config", "Config", "KT_Skill")

# Faction names (Vietnamese)
FACTION_NAMES = {
    1: "Thiếu Lâm",
    2: "Thiên Vương",
    3: "Đường Môn",
    4: "Ngũ Độc",
    5: "Nga My",
    6: "Côn Lôn",
    7: "Thiên Nhẫn",
    8: "Cái Bang",
    9: "Ngũ Tiên",
    10: "Võ Đang",
}


def to_snake_case(name):
    """Convert Vietnamese skill name to snake_case identifier."""
    # Vietnamese character mapping
    vn_map = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    }
    result = name.lower().strip()
    for vn, ascii_char in vn_map.items():
        result = result.replace(vn, ascii_char)
    # Replace non-alphanumeric with underscore
    result = re.sub(r'[^a-z0-9]+', '_', result)
    result = result.strip('_')
    return result


def parse_skill_data(filepath):
    """Parse SkillData.xml and return dict of skill_id -> skill_attrs."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    skills = {}
    for s in root.findall('Skill'):
        sid = int(s.get('ID', '0'))
        skills[sid] = {
            'id': sid,
            'name': s.get('Name', ''),
            'type': int(s.get('Type', '0')),
            'faction_id': int(s.get('FactionID', '0')),
            'is_melee': s.get('IsMelee', 'false') == 'true',
            'is_physical': s.get('IsPhysical', 'false') == 'true',
            'is_damage_skill': s.get('IsDamageSkill', 'false') == 'true',
            'cast_action_id': int(s.get('CastActionID', '0')),
            'bullet_id': int(s.get('BulletID', '0')),
            'bullet_count': int(s.get('BulletCount', '0')),
            'shoot_count': int(s.get('ShootCount', '-1')),
            'wait_time': int(s.get('WaitTime', '0')),
            'fixed_attack_action_count': int(s.get('FixedAttackActionCount', '-1')),
            'is_no_atk_speed_cd': s.get('IsSkillNoAddAttackSpeedCooldown', 'false') == 'true',
            'properties': s.get('Properties', 'empty'),
            'bullet_round_time': int(s.get('BulletRoundTime', '0')),
            'target_type': s.get('TargetType', ''),
            'skill_style': s.get('SkillStyle', ''),
            'attack_radius': int(s.get('AttackRadius', '0')),
            'is_bullet': int(s.get('IsBullet', '0')),
        }
    return skills


def parse_skill_properties(filepath):
    """Parse SkillPropertiesLua.xml -> dict of prop_name -> {symbol_name -> {level -> value}}."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    props = {}
    for skill in root.findall('Skill'):
        name = skill.get('Name')
        symbols = {}
        for sym in skill.findall('Symbol'):
            sym_name = sym.get('Name')
            level_values = {}
            for val in sym.findall('Value'):
                for lvl in val.findall('SkillLevelValue'):
                    level = int(lvl.get('Level'))
                    value = float(lvl.get('Value'))
                    if level not in level_values:
                        level_values[level] = value
            symbols[sym_name] = level_values
        props[name] = symbols
    return props


def parse_bullet_config(filepath):
    """Parse BulletConfig.xml -> dict of bullet_id -> bullet_attrs."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    bullets = {}
    for b in root.findall('Bullet'):
        bid = int(b.get('ID', '0'))
        bullets[bid] = {
            'id': bid,
            'name': b.get('Name', ''),
            'move_kind': int(b.get('MoveKind', '0')),
            'is_follow_target': int(b.get('IsFollowTarget', '0')),
            'explode_radius': int(b.get('ExplodeRadius', '0')),
            'damage_interval': int(b.get('DamageInterval', '0')),
            'life_time': int(b.get('LifeTime', '0')),
            'move_speed': int(b.get('MoveSpeed', '0')),
            'is_comeback': int(b.get('IsComeback', '0')),
            'max_target_touch': int(b.get('MaxTargetTouch', '1000')),
            'piece_through_percent': int(b.get('PieceThroughTargetsPercent', '0')),
        }
    return bullets


def get_cooldown_ticks(props, prop_name):
    """Get skill_mintimepercast_v at level 1 from properties, trying base name and _1 suffix."""
    candidates = [prop_name, prop_name + '_1']
    for candidate in candidates:
        if candidate in props:
            syms = props[candidate]
            if 'skill_mintimepercast_v' in syms:
                levels = syms['skill_mintimepercast_v']
                return int(levels.get(1, levels.get(min(levels.keys()), 0)))
    return 0


def get_state_time_ticks(props, prop_name):
    """Get skill_statetime at level 1 from properties."""
    candidates = [prop_name, prop_name + '_1']
    for candidate in candidates:
        if candidate in props:
            syms = props[candidate]
            if 'skill_statetime' in syms:
                levels = syms['skill_statetime']
                return int(levels.get(1, levels.get(min(levels.keys()), 0)))
    return 0


def classify_skill(skill, bullets):
    """Classify a skill into categories for phase calculation."""
    if skill['is_no_atk_speed_cd']:
        return 'instant'

    fixed_count = skill['fixed_attack_action_count']
    if fixed_count > 1:
        return 'multi_hit'

    if skill['is_melee'] and skill['is_physical']:
        return 'melee_physical'

    if skill['cast_action_id'] == 11:
        if skill['is_physical']:
            return 'ranged_physical_magic_cast'
        return 'magic'

    if skill['cast_action_id'] == 9:
        if skill['is_melee']:
            return 'melee_physical'
        return 'ranged_physical'

    if skill['bullet_id'] > 0:
        bullet = bullets.get(skill['bullet_id'], {})
        if bullet.get('move_kind', 0) > 0:
            return 'ranged_physical'
        return 'magic'

    return 'melee_physical'


def calculate_phases(skill, bullets, skill_class):
    """Calculate phase breakdown for a skill."""
    fixed_count = skill['fixed_attack_action_count']

    # Determine total_tick
    if skill_class == 'instant':
        total_tick = 6
    elif skill_class == 'multi_hit':
        # Multi-hit: each hit is (MaxDuration - Addition) / count
        per_hit = (MAX_ATK_DURATION - ATK_SPEED_ADDITION) / max(fixed_count, 1)
        total_tick = math.ceil(MAX_ATK_DURATION * TICK_RATE) + 2
    else:
        total_tick = math.ceil((MAX_ATK_DURATION + ATK_SPEED_ADDITION) * TICK_RATE)

    # Add WaitTime if present
    wait_ticks = 0
    if skill['wait_time'] > 0:
        wait_ticks = math.ceil(skill['wait_time'] / TICK_RATE)
        total_tick += wait_ticks

    # Global cooldown: minimum GCD at max attack speed
    if skill['is_no_atk_speed_cd']:
        gcd = math.ceil(MIN_ATK_DURATION * TICK_RATE) + 1
    else:
        gcd = math.ceil((MIN_ATK_DURATION + ATK_SPEED_ADDITION) * TICK_RATE)

    # Calculate phases based on class
    phases = {}
    T = total_tick

    if skill_class == 'instant':
        phases['cast_delay'] = {'start': 0, 'end': 1}
        phases['damage'] = {'tick': 2}
        phases['hit_stop'] = {'start': 2, 'end': 3}
        phases['recovery_lock'] = {'start': 3, 'end': 4}
        phases['combo_window'] = {'start': 4, 'end': 5}
        phases['idle'] = {'tick': T - 1}

    elif skill_class == 'multi_hit':
        per_hit_ticks = max(2, math.floor((T - 2) / fixed_count))
        cast_end = max(1, per_hit_ticks // 2 - 1)

        phases['cast_delay'] = {'start': 0, 'end': cast_end}

        # Multiple damage ticks
        damage_ticks = []
        for i in range(fixed_count):
            tick = cast_end + 1 + i * per_hit_ticks
            if tick < T:
                damage_ticks.append(tick)
        if not damage_ticks:
            damage_ticks = [cast_end + 1]

        if len(damage_ticks) == 1:
            phases['damage'] = {'tick': damage_ticks[0]}
        else:
            phases['damage'] = {'ticks': damage_ticks, 'interval': per_hit_ticks}

        last_dmg = damage_ticks[-1]
        hs_end = min(last_dmg + 1, T - 1)
        phases['hit_stop'] = {'start': last_dmg, 'end': hs_end}

        recovery_end = min(hs_end + max(2, (T - hs_end) // 2), T - 3)
        if recovery_end <= hs_end:
            recovery_end = min(hs_end + 2, T - 3)
        phases['recovery_lock'] = {'start': hs_end, 'end': recovery_end}

        combo_end = T - 2
        if combo_end <= recovery_end:
            combo_end = recovery_end + 1
        phases['combo_window'] = {'start': recovery_end + 1, 'end': combo_end}
        phases['idle'] = {'tick': T - 1}

    elif skill_class == 'melee_physical':
        cast_end = max(1, math.floor(T * 0.39))
        dmg_tick = cast_end + 1
        hs_end = dmg_tick + 1
        recovery_end = max(hs_end + 1, math.floor(T * 0.72))
        combo_start = recovery_end + 1
        combo_end = T - 2

        phases['cast_delay'] = {'start': 0 + wait_ticks, 'end': cast_end + wait_ticks}
        if wait_ticks > 0:
            phases['cast_delay']['start'] = 0
            phases['cast_delay']['end'] = cast_end + wait_ticks
        phases['damage'] = {'tick': dmg_tick + wait_ticks}
        phases['hit_stop'] = {'start': dmg_tick + wait_ticks, 'end': hs_end + wait_ticks}
        phases['recovery_lock'] = {'start': hs_end + wait_ticks, 'end': recovery_end + wait_ticks}
        if combo_start + wait_ticks <= combo_end + wait_ticks and combo_end + wait_ticks < T - 1:
            phases['combo_window'] = {'start': combo_start + wait_ticks, 'end': combo_end + wait_ticks}
        else:
            phases['combo_window'] = {'start': T - 3, 'end': T - 2}
        phases['idle'] = {'tick': T - 1}

    elif skill_class in ('ranged_physical', 'ranged_physical_magic_cast'):
        cast_end = max(1, math.floor(T * 0.33))
        dmg_tick = cast_end + 1  # Projectile launch
        recovery_end = max(dmg_tick + 2, math.floor(T * 0.67))
        combo_start = recovery_end + 1
        combo_end = T - 2

        phases['cast_delay'] = {'start': 0, 'end': cast_end}
        phases['damage'] = {'tick': dmg_tick}

        # Get bullet travel time for projectile arrival
        bullet = bullets.get(skill['bullet_id'], {})
        if bullet and bullet.get('life_time', 0) > 0:
            phases['projectile'] = {
                'launch_tick': dmg_tick,
                'life_time': bullet['life_time'],
                'move_speed': bullet.get('move_speed', 0)
            }
            if bullet.get('damage_interval', 0) > 0:
                phases['projectile']['damage_interval'] = bullet['damage_interval']

        phases['recovery_lock'] = {'start': dmg_tick + 1, 'end': recovery_end}
        phases['combo_window'] = {'start': combo_start, 'end': combo_end}
        phases['idle'] = {'tick': T - 1}

    elif skill_class == 'magic':
        cast_end = max(1, math.floor(T * 0.44))
        dmg_tick = cast_end + 1
        hs_end = dmg_tick + 1
        recovery_end = max(hs_end + 1, math.floor(T * 0.78))
        combo_start = recovery_end + 1
        combo_end = T - 2

        phases['cast_delay'] = {'start': 0, 'end': cast_end}
        phases['damage'] = {'tick': dmg_tick}
        phases['hit_stop'] = {'start': dmg_tick, 'end': hs_end}
        phases['recovery_lock'] = {'start': hs_end, 'end': recovery_end}
        phases['combo_window'] = {'start': combo_start, 'end': combo_end}
        phases['idle'] = {'tick': T - 1}

    return total_tick, gcd, phases


def generate_skill_frame_data(skill, props, bullets):
    """Generate frame data JSON entry for a single skill."""
    prop_name = skill['properties']
    if prop_name == 'empty':
        prop_name = ''

    # Get cooldown
    cooldown_tick = 0
    state_time_tick = 0
    if prop_name:
        cooldown_tick = get_cooldown_ticks(props, prop_name)
        state_time_tick = get_state_time_ticks(props, prop_name)

    # Classify and calculate phases
    skill_class = classify_skill(skill, bullets)
    total_tick, gcd, phases = calculate_phases(skill, bullets, skill_class)

    entry = {
        'skill_id': skill['id'],
        'skill_name': to_snake_case(skill['name']),
        'skill_name_vi': skill['name'],
        'faction': FACTION_NAMES.get(skill['faction_id'], 'Chung'),
        'total_tick': total_tick,
        'cooldown_tick': cooldown_tick,
        'global_cooldown_tick': gcd,
        'phases': phases,
        'input': {
            'buffer_window': 2
        },
        'properties': {
            'type': skill_class,
            'is_melee': skill['is_melee'],
            'is_physical': skill['is_physical'],
            'is_damage_skill': skill['is_damage_skill'],
            'cast_action_id': skill['cast_action_id'],
        }
    }

    # Add bullet info if applicable
    if skill['bullet_id'] > 0:
        bullet = bullets.get(skill['bullet_id'])
        if bullet:
            entry['bullet'] = {
                'id': bullet['id'],
                'name': bullet['name'],
                'life_time': bullet['life_time'],
                'move_speed': bullet['move_speed'],
                'explode_radius': bullet['explode_radius'],
                'damage_interval': bullet['damage_interval'],
            }

    # Add multi-hit info
    if skill['fixed_attack_action_count'] > 1:
        entry['properties']['fixed_attack_count'] = skill['fixed_attack_action_count']

    # Add state/buff duration
    if state_time_tick > 0:
        entry['state_duration_tick'] = state_time_tick

    return entry


def main():
    # Parse all XML configs
    print("Parsing SkillData.xml...")
    skills = parse_skill_data(os.path.join(BASE_DIR, "SkillData.xml"))
    print(f"  Loaded {len(skills)} skills")

    print("Parsing SkillPropertiesLua.xml...")
    props = parse_skill_properties(os.path.join(BASE_DIR, "SkillPropertiesLua.xml"))
    print(f"  Loaded {len(props)} skill property sets")

    print("Parsing BulletConfig.xml...")
    bullets = parse_bullet_config(os.path.join(BASE_DIR, "BulletConfig.xml"))
    print(f"  Loaded {len(bullets)} bullet configs")

    # Filter to player faction active skills (FactionID 1-10, or FactionID 0 with valid properties)
    # Include Type: 1 (Active), 2 (Buff/Toggle), 4 (Aura), 5 (Combat)
    active_types = {1, 2, 4, 5}
    player_factions = set(range(1, 11))

    # Collect all valid player skills
    player_skills = []
    for sid, skill in sorted(skills.items()):
        if skill['type'] not in active_types:
            continue
        if skill['faction_id'] not in player_factions:
            continue
        if skill['properties'] == 'empty':
            continue
        player_skills.append(skill)

    print(f"\nFiltered to {len(player_skills)} player faction active skills")

    # Generate frame data
    frame_data = {
        '_meta': {
            'tick_rate': TICK_RATE,
            'tick_duration_ms': round(1000 / TICK_RATE, 1),
            'min_attack_duration_s': MIN_ATK_DURATION,
            'max_attack_duration_s': MAX_ATK_DURATION,
            'attack_speed_addition_s': ATK_SPEED_ADDITION,
            'attack_speed_range': [0, 100],
            'notes': {
                'total_tick': 'Full action cycle in ticks (at base attack speed 0)',
                'cooldown_tick': 'Skill-specific cooldown in ticks (skill_mintimepercast_v)',
                'global_cooldown_tick': 'Minimum global cooldown between any two skills (at max attack speed 100)',
                'phases': 'Action phases with tick ranges',
                'buffer_window': 'Input buffer window for queuing next skill',
            }
        },
        'factions': {}
    }

    # Group by faction
    for skill in player_skills:
        faction_name = FACTION_NAMES.get(skill['faction_id'], 'Unknown')
        if faction_name not in frame_data['factions']:
            frame_data['factions'][faction_name] = []

        entry = generate_skill_frame_data(skill, props, bullets)
        frame_data['factions'][faction_name].append(entry)

    # Count totals
    total_entries = sum(len(v) for v in frame_data['factions'].values())
    print(f"Generated frame data for {total_entries} skills across {len(frame_data['factions'])} factions")

    # Write output
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "docs", "skill_frame_data.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(frame_data, f, indent=2, ensure_ascii=False)

    print(f"\nOutput written to: {output_path}")

    # Print summary
    print("\n=== Summary by Faction ===")
    for faction, entries in frame_data['factions'].items():
        dmg = sum(1 for e in entries if e['properties']['is_damage_skill'])
        buf = len(entries) - dmg
        print(f"  {faction}: {len(entries)} skills ({dmg} damage, {buf} buff/utility)")


if __name__ == '__main__':
    main()

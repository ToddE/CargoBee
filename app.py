import math
from flask import Flask, render_template, request
import os
from collections import Counter

app = Flask(__name__)

# --- Constants ---
APP_VERSION = os.getenv('APP_VERSION', '1.0.4Beta')
UMAMI_SCRIPT_URL = os.getenv('UMAMI_SCRIPT_URL')
UMAMI_WEBSITE_ID = os.getenv('UMAMI_WEBSITE_ID')
ROAD_WEIGHT_LIMIT_KG = 19950
CONTAINER_DOOR_HEIGHT_LIMIT_CM = 258 # Max physical height for a pallet to fit through the door
CONTAINERS = {
    '40ft_HC': {'name': "40' High Cube", 'length': 1203, 'width': 235, 'height': 269},
    '40ft': {'name': "40' Standard", 'length': 1203, 'width': 235, 'height': 239},
    '20ft': {'name': "20' Standard", 'length': 590, 'width': 235, 'height': 239}
}
CONTAINER_ORDER = ['20ft', '40ft', '40ft_HC']
PALLET_COLORS_HEX = {
    'Base': '#fbbf24',    # Corresponds to Three.js 0xfbbf24
    'Topper': '#60a5fa',  # Corresponds to Three.js 0x60a5fa
    'Remnant': '#f87171', # Corresponds to Three.js 0xf87171
    'default': '#9ca3af'
}


# Calculates how many items fit and the remaining space.
def calculate_remaining_space(container_dim, item_dim):
    if item_dim == 0:
        return 0, container_dim
    items_fit = math.floor(container_dim / item_dim)
    total_item_dim = items_fit * item_dim
    remaining_space = container_dim - total_item_dim
    return items_fit, round(remaining_space, 2)

# --- Helper function to simulate loading pallets into a single container ---
def simulate_single_container_load(container, pallet_inventory, pallet_configs, carton_weight, pallet_l, pallet_w, road_weight_limit):
    pallets_to_load = pallet_inventory.copy()
    # Ensure pallet dimensions are not zero to avoid division by zero error
    if pallet_l == 0 or pallet_w == 0:
        return []

    # Determine best orientation for pallets on the floor
    slots_l_wise = math.floor(container['length'] / pallet_l)
    slots_w_wise = math.floor(container['width'] / pallet_w)
    
    slots_l_rotated = math.floor(container['length'] / pallet_w)
    slots_w_rotated = math.floor(container['width'] / pallet_l)

    use_rotated_layout = (slots_l_rotated * slots_w_rotated) > (slots_l_wise * slots_w_wise)
    
    if use_rotated_layout:
        effective_pallet_l, effective_pallet_w = pallet_w, pallet_l
        floor_slots_x, floor_slots_y = slots_l_rotated, slots_w_rotated
    else:
        effective_pallet_l, effective_pallet_w = pallet_l, pallet_w
        floor_slots_x, floor_slots_y = slots_l_wise, slots_w_wise

    placed_pallets = []
    current_weight = 0

    # --- New "Greedy" Simulation Logic ---
    for x_idx in range(floor_slots_x):
        for y_idx in range(floor_slots_y):
            pos_x = x_idx * effective_pallet_l
            pos_y = y_idx * effective_pallet_w
            
            # 1. Try to place a full stack (Base + Topper)
            if 'Topper' in pallet_configs and pallets_to_load.get('Base', 0) > 0 and pallets_to_load.get('Topper', 0) > 0:
                base_info = pallet_configs['Base']
                topper_info = pallet_configs['Topper']
                stack_height = base_info['height'] + topper_info['height']
                stack_weight = (base_info['cartons'] * carton_weight + base_info.get('pallet_weight', 0)) + \
                               (topper_info['cartons'] * carton_weight + topper_info.get('pallet_weight', 0))
                
                if stack_height <= container['height'] and current_weight + stack_weight <= road_weight_limit:
                    placed_pallets.append({'type': 'Base', 'x': pos_x, 'y': pos_y, 'z': 0, 'l': effective_pallet_l, 'w': effective_pallet_w, 'h': base_info['height']})
                    placed_pallets.append({'type': 'Topper', 'x': pos_x, 'y': pos_y, 'z': base_info['height'], 'l': effective_pallet_l, 'w': effective_pallet_w, 'h': topper_info['height']})
                    pallets_to_load['Base'] -= 1
                    pallets_to_load['Topper'] -= 1
                    current_weight += stack_weight
                    continue # Move to next slot

            # 2. If not, try to place any single pallet (tallest first)
            pallet_priority = sorted([p for p in ['Base', 'Topper', 'Remnant'] if p in pallet_configs and pallets_to_load.get(p, 0) > 0],
                                     key=lambda p: pallet_configs[p]['height'], reverse=True)
            
            for p_type in pallet_priority:
                pallet_info = pallet_configs[p_type]
                pallet_weight = (pallet_info['cartons'] * carton_weight) + pallet_info.get('pallet_weight', 0)
                if pallet_info['height'] <= container['height'] and current_weight + pallet_weight <= road_weight_limit:
                    placed_pallets.append({'type': p_type, 'x': pos_x, 'y': pos_y, 'z': 0, 'l': effective_pallet_l, 'w': effective_pallet_w, 'h': pallet_info['height']})
                    pallets_to_load[p_type] -= 1
                    current_weight += pallet_weight
                    break # Pallet placed, move to next slot

    # --- Final Step: Calculate ACCURATE remaining floor space ---
    if not placed_pallets:
        return [], container['length'], container['width']

    # Find the actual dimensions used by the placed pallets
    max_x_used = max(p['x'] + p['l'] for p in placed_pallets)
    max_y_used = max(p['y'] + p['w'] for p in placed_pallets)

    rem_l = container['length'] - max_x_used
    rem_w = container['width'] - max_y_used

    # --- Apply Buffer for Visualization ---
    # This part is now only for the 3D view, not for core logic.
    # It distributes the calculated remaining space between the pallets that were actually placed.
    placed_xs = sorted(list(set(p['x'] for p in placed_pallets)))
    placed_ys = sorted(list(set(p['y'] for p in placed_pallets)))
    
    buffer_l = rem_l / len(placed_xs) if len(placed_xs) > 1 else 0
    buffer_w = rem_w / len(placed_ys) if len(placed_ys) > 1 else 0

    if buffer_l > 0 or buffer_w > 0:
        for pallet in placed_pallets:
            x_idx = placed_xs.index(pallet['x'])
            y_idx = placed_ys.index(pallet['y'])
            pallet['x'] += x_idx * buffer_l
            pallet['y'] += y_idx * buffer_w

    return placed_pallets, rem_l, rem_w

# --- Calculation Function for Floor-Loaded Shipments ---
def calculate_floor_load(form_inputs, road_weight_limit):
    total_cartons = int(form_inputs.get('total_cartons') or 0)
    carton_l = float(form_inputs.get('carton_l') or 0)
    carton_w = float(form_inputs.get('carton_w') or 0)
    carton_h = float(form_inputs.get('carton_h') or 0)
    carton_weight = float(form_inputs.get('carton_weight') or 0)


    if not all([total_cartons, carton_l, carton_w, carton_h, carton_weight]):
        raise ValueError("One or more required carton fields are zero or missing.")

    cartons_left_to_ship = total_cartons
    container_manifests = []

    while cartons_left_to_ship > 0:
        cartons_by_weight = math.floor(road_weight_limit / carton_weight) if carton_weight > 0 else float('inf')
        found_fit = False
        for key, container in reversed(list(CONTAINERS.items())):
            cartons_per_layer = max(math.floor(container['length']/carton_l) * math.floor(container['width']/carton_w), math.floor(container['length']/carton_w) * math.floor(container['width']/carton_l))
            if cartons_per_layer == 0: continue
            num_layers = math.floor(container['height'] / carton_h)
            cartons_by_volume = int(cartons_per_layer * num_layers)
            container_capacity = min(cartons_by_volume, cartons_by_weight)
            if cartons_left_to_ship <= container_capacity:
                container_manifests.append({'key': key, 'cartons': cartons_left_to_ship})
                cartons_left_to_ship = 0
                found_fit = True
                break
        
        if not found_fit:
            largest_key = list(CONTAINERS.keys())[0]
            container = CONTAINERS[largest_key]
            cartons_per_layer = max(math.floor(container['length']/carton_l) * math.floor(container['width']/carton_w), math.floor(container['length']/carton_w) * math.floor(container['width']/carton_l))
            num_layers = math.floor(container['height'] / carton_h)
            cartons_by_volume = cartons_per_layer * num_layers
            if cartons_by_volume == 0: raise Exception("A single carton is too large for any container.")
            container_capacity = min(cartons_by_volume, cartons_by_weight)
            container_manifests.append({'key': largest_key, 'cartons': container_capacity})
            cartons_left_to_ship -= container_capacity

    container_counts = Counter(c['key'] for c in container_manifests)
    final_recommendation_str = " & ".join([f"{count} x {CONTAINERS[key]['name']}" for key, count in sorted(container_counts.items(), reverse=True)])

    detailed_configs = []
    is_overweight = False
    for i, c in enumerate(container_manifests):
        container_weight = c['cartons'] * carton_weight
        if container_weight > road_weight_limit: is_overweight = True
        detailed_configs.append({
            'name': f"Container {i+1}: {CONTAINERS[c['key']]['name']}",
            'weight': round(container_weight, 2),
            'items': [f"Floor-loaded with {c['cartons']} cartons."]
        })
    # final_results = {'recommendation': final_recommendation_str, 'pallet_configs': detailed_configs}

    first_container_key = container_manifests[0]['key']
    first_container = CONTAINERS[first_container_key]
    _, rem_l = calculate_remaining_space(first_container['length'], carton_l)
    _, rem_w = calculate_remaining_space(first_container['width'], carton_w)

    final_results = {
        'recommendation': final_recommendation_str, 
        'pallet_configs': detailed_configs,
        'remaining_l': rem_l,
        'remaining_w': rem_w
    }

    final_results['weight_status'] = "OVERWEIGHT" if is_overweight else "OK"
    return final_results

# --- Calculation Function for Palletized Shipments ---
def calculate_palletized_load(form_inputs, road_weight_limit):
    total_cartons = int(form_inputs.get('total_cartons') or 0)
    carton_l = float(form_inputs.get('carton_l') or 0)
    carton_w = float(form_inputs.get('carton_w') or 0)
    carton_h = float(form_inputs.get('carton_h') or 0)
    carton_weight = float(form_inputs.get('carton_weight') or 0)
    pallet_weight = float(form_inputs.get('pallet_weight') or 0)
    pallet_l = float(form_inputs.get('pallet_l') or 0)
    pallet_w = float(form_inputs.get('pallet_w') or 0)
    pallet_h = float(form_inputs.get('pallet_h') or 0)
    max_pallet_h_from_user = float(form_inputs.get('max_pallet_h') or 0)

   

    if not all([total_cartons, carton_l, carton_w, carton_h, carton_weight, pallet_l, pallet_w, pallet_h, max_pallet_h_from_user]):
        raise ValueError("One or more required carton or pallet fields are zero or missing.")

    max_pallet_h = min(max_pallet_h_from_user, CONTAINER_DOOR_HEIGHT_LIMIT_CM)

    # Old cartons_per_layer without padding below:
    cartons_per_layer = max(math.floor(pallet_l / carton_l) * math.floor(pallet_w / carton_w), math.floor(pallet_l / carton_w) * math.floor(pallet_w / carton_l))
    if cartons_per_layer == 0: raise ValueError("Carton is larger than the pallet base.")

    layers_A = math.floor((max_pallet_h - pallet_h) / carton_h)
    if layers_A <= 0: raise ValueError("Cannot build a base pallet within warehouse/door height limit.")

    pallet_configs = { 'l': pallet_l, 'w': pallet_w, 'Base': {'layers': layers_A, 'cartons': layers_A * cartons_per_layer, 'height': round((layers_A * carton_h) + pallet_h, 2), 'pallet_weight': pallet_weight} }

    cartons_to_assign = total_cartons
    total_pallet_inventory = Counter()
    num_base_only = cartons_to_assign // pallet_configs['Base']['cartons']
    if num_base_only > 0:
        total_pallet_inventory['Base'] = num_base_only
        cartons_to_assign %= pallet_configs['Base']['cartons']
    if cartons_to_assign > 0:
        layers_remnant = math.ceil(cartons_to_assign / cartons_per_layer)
        pallet_configs['Remnant'] = {'layers': layers_remnant, 'cartons': cartons_to_assign, 'height': round((layers_remnant * carton_h) + pallet_h, 2), 'pallet_weight': pallet_weight}
        total_pallet_inventory['Remnant'] = 1

    # --- Two-Pass Calculation: First without toppers, then check if toppers provide a better solution ---
    # Pass 1: Calculate with the simplest pallet configuration.
    base_container_manifests = _calculate_shipment_plan(total_pallet_inventory.copy(), pallet_configs, carton_weight, pallet_l, pallet_w, road_weight_limit, CONTAINER_ORDER)
    # Pass 2: Check if using Toppers results in a better plan (fewer containers).
    final_container_manifests, final_pallet_configs = _optimize_with_toppers(base_container_manifests, total_cartons, pallet_configs, cartons_per_layer, carton_h, carton_weight, pallet_l, pallet_w, road_weight_limit)

    total_pallets_built = sum(total_pallet_inventory.values())
    container_counts = Counter(c['key'] for c in final_container_manifests)
    final_recommendation_str = " & ".join([f"{count} x {CONTAINERS[key]['name']}" for key, count in sorted(container_counts.items(), reverse=True)])

    detailed_configs = []
    is_overweight = False
    for i, c in enumerate(final_container_manifests):
        container_weight = 0
        # Rerun simulation for this specific container to get accurate remaining space
        c['items_3d'], rem_l, rem_w = simulate_single_container_load(CONTAINERS[c['key']], c['manifest'].copy(), final_pallet_configs, carton_weight, pallet_l, pallet_w, road_weight_limit)
        container_detail = {
            'name': f"Container {i+1}: {CONTAINERS[c['key']]['name']}", 
            'weight': 0, 
            'items': [],
            'viz_data': {'container': CONTAINERS[c['key']], 'items': c['items_3d']},
            'remaining_space': {'l': round(rem_l, 2), 'w': round(rem_w, 2)}
        }
        for p_type, count in sorted(c['manifest'].items(), key=lambda item: final_pallet_configs[item[0]]['height'], reverse=True):
            conf = final_pallet_configs[p_type]
            
            single_pallet_total_weight = (conf['cartons'] * carton_weight) + conf.get('pallet_weight', 0)
            
            container_weight += count * single_pallet_total_weight

            color = PALLET_COLORS_HEX.get(p_type, PALLET_COLORS_HEX['default'])
            desc_parts = [
                            f"<span style='color: {color};'>■</span> <strong>{count}x {p_type} Pallet(s)</strong> ({conf['layers']} layers)",
                            f"Pallet Height: {conf['height']}cm tall",
                            f"Capacity: <strong>{conf['cartons']}</strong> cartons/pallet",
                            f"Pallet Weight: {round(single_pallet_total_weight, 2)}kg"
                        ]
            container_detail['items'].append("<br>".join(desc_parts))

        container_detail['weight'] = round(container_weight, 2)
        if container_weight > road_weight_limit: is_overweight = True
        detailed_configs.append(container_detail)

    final_results = {
        'total_pallets': total_pallets_built, 
        'pallet_configs': detailed_configs, 
        'recommendation': final_recommendation_str,
    }
    final_results['weight_status'] = "OVERWEIGHT" if is_overweight else "OK"
    return final_results

def _optimize_with_toppers(original_manifests, total_cartons, original_pallet_configs, cartons_per_layer, carton_h, carton_weight, pallet_l, pallet_w, road_weight_limit):
    """
    A second-pass function to check if re-calculating with Topper pallets can result in a better (fewer containers) solution.
    """
    # Toppers are only useful if they can be stacked, which requires a High Cube container.
    hc_container = CONTAINERS['40ft_HC']
    pallet_h = original_pallet_configs.get('h', 15) # Assuming pallet height is stored in pallet_configs
    remaining_space = hc_container['height'] - original_pallet_configs['Base']['height']
    layers_B = math.floor((remaining_space - pallet_h) / carton_h) if remaining_space > pallet_h else 0

    if layers_B <= 0:
        return original_manifests, original_pallet_configs # Toppers are not possible, return original plan and configs.

    # Create a new pallet_configs with toppers
    optimized_pallet_configs = original_pallet_configs.copy()
    optimized_pallet_configs['Topper'] = {'layers': layers_B, 'cartons': layers_B * cartons_per_layer, 'height': round((layers_B * carton_h) + pallet_h, 2), 'pallet_weight': original_pallet_configs['Base']['pallet_weight']}

    # Re-calculate the entire pallet inventory with Base+Topper stacks
    cartons_to_assign = total_cartons
    optimized_inventory = Counter()
    cartons_per_stack = optimized_pallet_configs['Base']['cartons'] + optimized_pallet_configs['Topper']['cartons']
    num_stacks = cartons_to_assign // cartons_per_stack
    optimized_inventory['Base'] = num_stacks
    optimized_inventory['Topper'] = num_stacks
    cartons_to_assign %= cartons_per_stack
    num_base = cartons_to_assign // optimized_pallet_configs['Base']['cartons']
    if num_base > 0:
        optimized_inventory['Base'] += num_base
        cartons_to_assign -= num_base * optimized_pallet_configs['Base']['cartons']
    
    if cartons_to_assign > 0:
        layers_remnant = math.ceil(cartons_to_assign / cartons_per_layer)
        # Ensure Remnant config is added if it will be used.
        if 'Remnant' not in optimized_pallet_configs:
             optimized_pallet_configs['Remnant'] = {'layers': layers_remnant, 'cartons': cartons_to_assign, 'height': round((layers_remnant * carton_h) + pallet_h, 2), 'pallet_weight': original_pallet_configs['Base']['pallet_weight']}
        optimized_inventory['Remnant'] = 1

    # Re-run the shipment plan with the new inventory
    optimized_manifests = _calculate_shipment_plan(optimized_inventory, optimized_pallet_configs, carton_weight, pallet_l, pallet_w, road_weight_limit, CONTAINER_ORDER)

    # Return the plan with fewer containers. If equal, prefer the original (simpler) plan.
    if len(optimized_manifests) < len(original_manifests):
        return optimized_manifests, optimized_pallet_configs
    else:
        return original_manifests, original_pallet_configs

def _calculate_shipment_plan(total_pallet_inventory, pallet_configs, carton_weight, pallet_l, pallet_w, road_weight_limit, allowed_containers):
    pallets_left_to_ship = total_pallet_inventory.copy()
    container_manifests = []

    while sum(pallets_left_to_ship.values()) > 0:
        best_fit_container_key = None
        pallets_for_best_fit = []

        # --- 1. Check if all remaining pallets can fit in a single container ---
        # For leftovers, check smallest first to be efficient. For the whole shipment, check largest first.
        check_order = allowed_containers # Always check smallest first for best single container fit
        for key in check_order:
            if key not in allowed_containers: continue
            container = CONTAINERS[key]
            pallets_packed_this_round, _, _ = simulate_single_container_load(container, pallets_left_to_ship.copy(), pallet_configs, carton_weight, pallet_l, pallet_w, road_weight_limit)
            if len(pallets_packed_this_round) >= sum(pallets_left_to_ship.values()):
                best_fit_container_key = key # Found a container that fits everything
                pallets_for_best_fit = pallets_packed_this_round
                break

        if best_fit_container_key:
            manifest_summary = Counter(p['type'] for p in pallets_for_best_fit)
            container_manifests.append({'key': best_fit_container_key, 'manifest': manifest_summary, 'items_3d': pallets_for_best_fit})
            pallets_left_to_ship.clear()
        else: # The entire shipment does not fit into a single container.
            # Attempt to find an optimal 2-container solution.
            optimal_primary_key = None
            optimal_primary_packed_pallets = []
            optimal_secondary_key = None
            optimal_secondary_packed_pallets = []
            
            min_total_container_cost = float('inf')
            # Define relative costs based on CONTAINER_ORDER (20ft=1, 40ft=2, 40ft_HC=3)
            container_costs = {key: i + 1 for i, key in enumerate(CONTAINER_ORDER)}

            # Iterate through potential primary containers from LARGEST to SMALLEST.
            # This prioritizes larger primary containers for equal-cost 2-container solutions,
            # fulfilling the "fill the first container as much as possible" requirement.
            for primary_candidate_key in reversed(allowed_containers):
                primary_container = CONTAINERS[primary_candidate_key]

                primary_packed_pallets_candidate, _, _ = simulate_single_container_load(
                    primary_container,
                    pallets_left_to_ship.copy(),
                    pallet_configs, carton_weight, pallet_l, pallet_w, road_weight_limit
                )

                if not primary_packed_pallets_candidate:
                    continue # This primary container can't even hold one pallet, skip.

                current_pallets_remaining = pallets_left_to_ship.copy()
                for p in primary_packed_pallets_candidate:
                    # This check is crucial to prevent KeyErrors if a pallet type from the manifest isn't in the inventory
                    if p['type'] in current_pallets_remaining:
                        current_pallets_remaining[p['type']] -= 1
                current_pallets_remaining = +current_pallets_remaining # Clean up zero counts

                # If after filling the primary, no pallets remain, it means this primary container
                # could fit everything. This should ideally be caught by the initial single-container check.
                # We continue here to prioritize finding a 2-container solution if one exists and is cheaper.
                if not current_pallets_remaining:
                    continue 

                # Now, try to fit the `current_pallets_remaining` into a *single* secondary container.
                # Iterate through secondary containers from SMALLEST to LARGEST.
                for secondary_candidate_key in allowed_containers:
                    secondary_container = CONTAINERS[secondary_candidate_key]
                    secondary_packed_pallets_candidate, _, _ = simulate_single_container_load(
                        secondary_container,
                        current_pallets_remaining.copy(),
                        pallet_configs, carton_weight, pallet_l, pallet_w, road_weight_limit
                    )

                    if len(secondary_packed_pallets_candidate) >= sum(current_pallets_remaining.values()):
                        # Found a valid 2-container solution: primary_candidate_key + secondary_candidate_key.
                        current_total_cost = container_costs[primary_candidate_key] + container_costs[secondary_candidate_key]

                        if current_total_cost < min_total_container_cost:
                            min_total_container_cost = current_total_cost
                            optimal_primary_key = primary_candidate_key
                            optimal_primary_packed_pallets = primary_packed_pallets_candidate
                            optimal_secondary_key = secondary_candidate_key
                            optimal_secondary_packed_pallets = secondary_packed_pallets_candidate
                        # No need for tie-breaker here, as primary iteration order handles "largest primary" preference.
                        break # Found the smallest secondary for this primary, move to next primary candidate.

            # Apply the found optimal 2-container solution, or fall back to single largest container.
            if optimal_primary_key and optimal_secondary_key:
                primary_manifest_summary = Counter(p['type'] for p in optimal_primary_packed_pallets)
                container_manifests.append({'key': optimal_primary_key, 'manifest': primary_manifest_summary, 'items_3d': optimal_primary_packed_pallets})

                for p_type, count in primary_manifest_summary.items():
                    pallets_left_to_ship[p_type] -= count
                pallets_left_to_ship = +pallets_left_to_ship # Clean up zero counts

                secondary_manifest_summary = Counter(p['type'] for p in optimal_secondary_packed_pallets)
                container_manifests.append({'key': optimal_secondary_key, 'manifest': secondary_manifest_summary, 'items_3d': optimal_secondary_packed_pallets})
                pallets_left_to_ship.clear() # All pallets are now assigned.

            else:
                # Fallback: No 1- or 2-container solution found by the optimization.
                # This means the shipment needs 3+ containers, or a single pallet is too large.
                # Fill the largest container possible and let the loop continue.
                largest_allowed_container_key = [c for c in reversed(allowed_containers) if c in allowed_containers][0]
                largest_container = CONTAINERS[largest_allowed_container_key]
                potential_pack, _, _ = simulate_single_container_load(largest_container, pallets_left_to_ship.copy(), pallet_configs, carton_weight, pallet_l, pallet_w, road_weight_limit)
                
                if not potential_pack:
                    raise Exception("Could not pack any more pallets. A single remaining pallet may be too heavy or large for the allowed containers.")

                partial_manifest = Counter(p['type'] for p in potential_pack)
                container_manifests.append({'key': largest_allowed_container_key, 'manifest': partial_manifest.copy(), 'items_3d': potential_pack}) # Populate items_3d
                
                for p_type, count in partial_manifest.items():
                    pallets_left_to_ship[p_type] -= count
                pallets_left_to_ship = +pallets_left_to_ship # Clean up zero counts

    return container_manifests

# --- Main Application Route ---
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        form_inputs = request.form.copy()
    elif request.args:
        form_inputs = request.args.copy()
    else:
        # Default values for a fresh page load
        form_inputs = {
            'total_cartons': '', 'carton_weight': '', 'carton_l': '', 'carton_w': '', 'carton_h': '',
            'pallet_l': '120', 'pallet_w': '100', 'pallet_h': '15', 'pallet_weight': '20', 'max_pallet_h': '152.4',
            'road_weight_limit': str(ROAD_WEIGHT_LIMIT_KG)
        }

    context = {
        'containers': CONTAINERS, 
        'form_inputs': form_inputs, 
        'version': APP_VERSION, 
        'road_weight_limit': ROAD_WEIGHT_LIMIT_KG,
        'umami_script_url': UMAMI_SCRIPT_URL,
        'umami_website_id': UMAMI_WEBSITE_ID
    }

    # Only run calculations if there's something to calculate
    if request.method == 'POST' or 'total_cartons' in request.args:
        try:
            road_weight_limit = float(form_inputs.get('road_weight_limit') or ROAD_WEIGHT_LIMIT_KG)
            shipment_type = form_inputs.get('shipment_type')
            
            if shipment_type == 'floor_loaded':
                final_results = calculate_floor_load(form_inputs, road_weight_limit)
            else: # Palletized is the default
                final_results = calculate_palletized_load(form_inputs, road_weight_limit)
            
            total_cartons = int(form_inputs.get('total_cartons') or 0)
            carton_weight = float(form_inputs.get('carton_weight') or 0)
            total_cargo_weight = total_cartons * carton_weight

            if shipment_type != 'floor_loaded':
                 pallet_weight = float(form_inputs.get('pallet_weight') or 0)
                 total_cargo_weight += final_results.get('total_pallets', 0) * pallet_weight

            final_results['total_weight_kg'] = round(total_cargo_weight, 2)
            context['results'] = final_results

        except Exception as e:
            context['error'] = f"Calculation Error: {e}"

    return render_template('index.html', **context)

if __name__ == '__main__':
    app.run(debug=True)
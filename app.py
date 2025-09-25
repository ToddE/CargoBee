import math
from flask import Flask, render_template, request
import os
from collections import Counter

app = Flask(__name__)

# --- Constants ---
APP_VERSION = os.getenv('APP_VERSION', '1.0.0Beta')
ROAD_WEIGHT_LIMIT_KG = 19950
CONTAINER_DOOR_HEIGHT_LIMIT_CM = 258 # Max physical height for a pallet to fit through the door
CONTAINERS = {
    '40ft_HC': {'name': "40' High Cube", 'length': 1203, 'width': 235, 'height': 269},
    '40ft': {'name': "40' Standard", 'length': 1203, 'width': 235, 'height': 239},
    '20ft': {'name': "20' Standard", 'length': 590, 'width': 235, 'height': 239}
}

# --- Helper function to simulate loading pallets into a single container ---
def simulate_single_container_load(container, pallet_inventory, pallet_configs, carton_weight):
    pallets_to_load = pallet_inventory.copy()
    floor_slots = max(math.floor(container['length']/pallet_configs['l']) * math.floor(container['width']/pallet_configs['w']), math.floor(container['length']/pallet_configs['w']) * math.floor(container['width']/pallet_configs['l']))
    
    pallets_that_fit = []
    current_weight = 0
    
    for _ in range(floor_slots):
        remaining_h = container['height']
        while True:
            best_pallet_to_add = None
            for p_type in sorted(pallets_to_load.keys(), key=lambda k: pallet_configs.get(k, {}).get('height', 0), reverse=True):
                if pallets_to_load.get(p_type, 0) > 0 and pallet_configs.get(p_type, {}).get('height', 0) <= remaining_h:
                    pallet_info = pallet_configs[p_type]
                    pallet_weight = (pallet_info['cartons'] * carton_weight) + pallet_info.get('pallet_weight', 0)
                    if current_weight + pallet_weight <= ROAD_WEIGHT_LIMIT_KG:
                        best_pallet_to_add = p_type
                        break 
            
            if best_pallet_to_add:
                pallet_info = pallet_configs[best_pallet_to_add]
                pallet_weight = (pallet_info['cartons'] * carton_weight) + pallet_info.get('pallet_weight', 0)
                
                pallets_that_fit.append(best_pallet_to_add)
                pallets_to_load[best_pallet_to_add] -= 1
                remaining_h -= pallet_info['height']
                current_weight += pallet_weight
            else:
                break 
                
    return pallets_that_fit

# --- Calculation Function for Floor-Loaded Shipments ---
def calculate_floor_load(form_inputs):
    total_cartons = int(form_inputs['total_cartons'])
    carton_l, carton_w, carton_h = float(form_inputs['carton_l']), float(form_inputs['carton_w']), float(form_inputs['carton_h'])
    carton_weight = float(form_inputs['carton_weight'])

    cartons_left_to_ship = total_cartons
    container_manifests = []

    while cartons_left_to_ship > 0:
        cartons_by_weight = math.floor(ROAD_WEIGHT_LIMIT_KG / carton_weight) if carton_weight > 0 else float('inf')
        found_fit = False
        for key, container in reversed(list(CONTAINERS.items())):
            cartons_per_layer = max(math.floor(container['length']/carton_l) * math.floor(container['width']/carton_w), math.floor(container['length']/carton_w) * math.floor(container['width']/carton_l))
            if cartons_per_layer == 0: continue
            num_layers = math.floor(container['height'] / carton_h)
            cartons_by_volume = cartons_per_layer * num_layers
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
        if container_weight > ROAD_WEIGHT_LIMIT_KG: is_overweight = True
        detailed_configs.append({
            'name': f"Container {i+1}: {CONTAINERS[c['key']]['name']}",
            'weight': round(container_weight, 2),
            'items': [f"Floor-loaded with {c['cartons']} cartons."]
        })
    final_results = {'recommendation': final_recommendation_str, 'pallet_configs': detailed_configs}
    final_results['weight_status'] = "OVERWEIGHT" if is_overweight else "OK"
    return final_results

# --- Calculation Function for Palletized Shipments ---
def calculate_palletized_load(form_inputs):
    total_cartons = int(form_inputs['total_cartons'])
    carton_l, carton_w, carton_h = float(form_inputs['carton_l']), float(form_inputs['carton_w']), float(form_inputs['carton_h'])
    carton_weight = float(form_inputs['carton_weight'])
    pallet_weight = float(form_inputs.get('pallet_weight', 0))
    pallet_l, pallet_w, pallet_h = float(form_inputs['pallet_l']), float(form_inputs['pallet_w']), float(form_inputs['pallet_h'])
    
    # Use the lesser of the user's warehouse height and the container door limit
    max_pallet_h_from_user = float(form_inputs['max_pallet_h'])
    max_pallet_h = min(max_pallet_h_from_user, CONTAINER_DOOR_HEIGHT_LIMIT_CM)
    
    cartons_per_layer = max(math.floor(pallet_l / carton_l) * math.floor(pallet_w / carton_w), math.floor(pallet_l / carton_w) * math.floor(pallet_w / carton_l))
    if cartons_per_layer == 0: raise ValueError("Carton is larger than the pallet base.")

    layers_A = math.floor((max_pallet_h - pallet_h) / carton_h)
    if layers_A <= 0: raise ValueError("Cannot build a base pallet within warehouse/door height limit.")
    pallet_configs = { 'l': pallet_l, 'w': pallet_w, 'Base': {'layers': layers_A, 'cartons': layers_A * cartons_per_layer, 'height': round((layers_A * carton_h) + pallet_h, 2), 'pallet_weight': pallet_weight} }
    
    temp_container = CONTAINERS[list(CONTAINERS.keys())[0]]
    remaining_space = temp_container['height'] - pallet_configs['Base']['height']
    layers_B = math.floor((remaining_space - pallet_h) / carton_h) if remaining_space > pallet_h else 0
    if layers_B > 0:
        pallet_configs['Topper'] = {'layers': layers_B, 'cartons': layers_B * cartons_per_layer, 'height': round((layers_B * carton_h) + pallet_h, 2), 'pallet_weight': pallet_weight}

    cartons_to_assign = total_cartons
    total_pallet_inventory = {}
    if 'Topper' in pallet_configs:
        cartons_per_stack = pallet_configs['Base']['cartons'] + pallet_configs['Topper']['cartons']
        num_stacks = cartons_to_assign // cartons_per_stack
        if num_stacks > 0:
            total_pallet_inventory['Base'] = total_pallet_inventory.get('Base', 0) + num_stacks
            total_pallet_inventory['Topper'] = total_pallet_inventory.get('Topper', 0) + num_stacks
            cartons_to_assign %= cartons_per_stack
    num_base_only = cartons_to_assign // pallet_configs['Base']['cartons']
    if num_base_only > 0:
        total_pallet_inventory['Base'] = total_pallet_inventory.get('Base', 0) + num_base_only
        cartons_to_assign %= pallet_configs['Base']['cartons']
    if cartons_to_assign > 0:
        layers_remnant = math.ceil(cartons_to_assign / cartons_per_layer)
        pallet_configs['Remnant'] = {'layers': layers_remnant, 'cartons': cartons_to_assign, 'height': round((layers_remnant * carton_h) + pallet_h, 2), 'pallet_weight': pallet_weight}
        total_pallet_inventory['Remnant'] = 1
    
    pallets_left_to_ship = total_pallet_inventory.copy()
    container_manifests = []
    # fixed loop block
    while sum(pallets_left_to_ship.values()) > 0:
            # This logic is simpler: always try to pack remaining pallets into the largest available container type.
            largest_key = list(CONTAINERS.keys())[0] # This assumes '40ft_HC' is first
            largest_container = CONTAINERS[largest_key]

            # Simulate loading this single container
            pallets_packed_this_round = simulate_single_container_load(largest_container, pallets_left_to_ship, pallet_configs, carton_weight)

            # If we simulate and find that not a single pallet can be packed, then the remaining pallets are impossible to ship.
            if not pallets_packed_this_round:
                raise Exception("Remaining pallets cannot be packed. A single pallet may be too heavy or large for any container.")

            # Create a manifest of what was successfully packed in this round
            manifest = Counter(pallets_packed_this_round)
            container_manifests.append({'key': largest_key, 'manifest': dict(manifest)})

            # CRITICAL FIX: Subtract the packed pallets from the list of pallets left to ship
            for p_type, count in manifest.items():
                pallets_left_to_ship[p_type] -= count
            
            # Remove any pallet types that have been fully shipped
            pallets_left_to_ship = {ptype: count for ptype, count in pallets_left_to_ship.items() if count > 0}

    total_pallets_built = sum(total_pallet_inventory.values())
    container_counts = Counter(c['key'] for c in container_manifests)
    final_recommendation_str = " & ".join([f"{count} x {CONTAINERS[key]['name']}" for key, count in sorted(container_counts.items(), reverse=True)])
    
    detailed_configs = []
    is_overweight = False
    for i, c in enumerate(container_manifests):
        container_weight = 0
        container_detail = {'name': f"Container {i+1}: {CONTAINERS[c['key']]['name']}", 'weight': 0, 'items': []}
        for p_type, count in sorted(c['manifest'].items(), key=lambda item: pallet_configs[item[0]]['height'], reverse=True):
            conf = pallet_configs[p_type]
            
            # Create the variable for a single loaded pallet's weight
            single_pallet_total_weight = (conf['cartons'] * carton_weight) + conf.get('pallet_weight', 0)
            
            # Add the weight of all pallets of this type to the container's total
            container_weight += count * single_pallet_total_weight

            # Create the formatted, multi-line description using the new variable
            desc_parts = [
                            f"<strong>{count} pallet(s) with {conf['layers']} layers</strong>",
                            f"Pallet Height: {conf['height']}cm tall",
                            f"Pallet Capacity: {conf['cartons']} cartons/pallet",
                            f"Pallet Weight: {round(single_pallet_total_weight, 2)}kg"
                        ]
            container_detail['items'].append("<br>".join(desc_parts))

        container_detail['weight'] = round(container_weight, 2)
        if container_weight > ROAD_WEIGHT_LIMIT_KG: is_overweight = True
        detailed_configs.append(container_detail)

    final_results = {'total_pallets': total_pallets_built, 'pallet_configs': detailed_configs, 'recommendation': final_recommendation_str}
    final_results['weight_status'] = "OVERWEIGHT" if is_overweight else "OK"
    return final_results

# --- Main Application Route ---
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        form_inputs = request.form.copy()
    elif request.args:
        form_inputs = request.args.copy()
    else:
        form_inputs = {
            'total_cartons': '', 'carton_weight': '', 'carton_l': '', 'carton_w': '', 'carton_h': '',
            'pallet_l': '120', 'pallet_w': '100', 'pallet_h': '15', 'pallet_weight': '20', 'max_pallet_h': '152.4'
        }

    context = {'containers': CONTAINERS, 'form_inputs': form_inputs, 'version': APP_VERSION, 'road_weight_limit': ROAD_WEIGHT_LIMIT_KG}

    if request.method == 'POST':
        try:
            shipment_type = form_inputs.get('shipment_type')
            
            if shipment_type == 'floor_loaded':
                final_results = calculate_floor_load(form_inputs)
            else: # Palletized
                final_results = calculate_palletized_load(form_inputs)
            
            total_cartons = int(form_inputs['total_cartons'])
            carton_weight = float(form_inputs['carton_weight'])
            total_cargo_weight = total_cartons * carton_weight
            if shipment_type != 'floor_loaded':
                 pallet_weight = float(form_inputs.get('pallet_weight', 0))
                 total_cargo_weight += final_results.get('total_pallets', 0) * pallet_weight

            final_results['total_weight_kg'] = round(total_cargo_weight, 2)
            context['results'] = final_results

        except Exception as e:
            context['error'] = f"Calculation Error: {e}"

    return render_template('index.html', **context)

if __name__ == '__main__':
    app.run(debug=True)
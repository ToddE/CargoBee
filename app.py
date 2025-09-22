import math
from flask import Flask, render_template, request
import os
from collections import Counter

app = Flask(__name__)

# --- Constants ---
APP_VERSION = os.getenv('APP_VERSION', '0.1.250919f')
ROAD_WEIGHT_LIMIT_KG = 19950 
CONTAINERS = {
    '40ft_HC': {'name': "40' High Cube", 'length': 1203, 'width': 235, 'height': 269},
    '40ft': {'name': "40' Standard", 'length': 1203, 'width': 235, 'height': 239},
    '20ft': {'name': "20' Standard", 'length': 590, 'width': 235, 'height': 239}
}

# --- Helper function to simulate loading pallets into a single container ---
def simulate_single_container_load(container, pallet_inventory, pallet_configs):
    pallets_to_load = pallet_inventory.copy()
    floor_slots = max(math.floor(container['length']/pallet_configs['l']) * math.floor(container['width']/pallet_configs['w']), math.floor(container['length']/pallet_configs['w']) * math.floor(container['width']/pallet_configs['l']))
    
    pallets_that_fit = []
    
    for _ in range(floor_slots):
        remaining_h = container['height']
        while True:
            best_pallet_to_add = None
            for p_type in sorted(pallets_to_load.keys(), key=lambda k: pallet_configs.get(k, {}).get('height', 0), reverse=True):
                if pallets_to_load.get(p_type, 0) > 0 and pallet_configs.get(p_type, {}).get('height', 0) <= remaining_h:
                    best_pallet_to_add = p_type
                    break
            
            if best_pallet_to_add:
                pallets_that_fit.append(best_pallet_to_add)
                pallets_to_load[best_pallet_to_add] -= 1
                remaining_h -= pallet_configs[best_pallet_to_add]['height']
            else:
                break
                
    return pallets_that_fit

# --- Main Application Route ---
@app.route('/', methods=['GET', 'POST'])
def home():
    form_inputs = request.form.copy() if request.method == 'POST' else request.args.copy()
    context = {'containers': CONTAINERS, 'form_inputs': form_inputs, 'version': APP_VERSION, 'road_weight_limit': ROAD_WEIGHT_LIMIT_KG}

    if request.method == 'POST':
        try:
            shipment_type = form_inputs.get('shipment_type')
            total_cartons = int(form_inputs['total_cartons'])
            carton_l, carton_w, carton_h = float(form_inputs['carton_l']), float(form_inputs['carton_w']), float(form_inputs['carton_h'])
            carton_weight = float(form_inputs['carton_weight'])
            
            final_results = {}
            recommended_containers = {}

            if shipment_type == 'floor_loaded':
                cartons_left_to_ship = total_cartons
                while cartons_left_to_ship > 0:
                    found_fit = False
                    for key, container in reversed(list(CONTAINERS.items())):
                        cartons_per_layer = max(math.floor(container['length']/carton_l) * math.floor(container['width']/carton_w), math.floor(container['length']/carton_w) * math.floor(container['width']/carton_l))
                        if cartons_per_layer == 0: continue
                        num_layers = math.floor(container['height'] / carton_h)
                        total_fit = cartons_per_layer * num_layers
                        if cartons_left_to_ship <= total_fit:
                            recommended_containers[key] = recommended_containers.get(key, 0) + 1
                            cartons_left_to_ship = 0
                            found_fit = True
                            break
                    if not found_fit:
                        largest_key = list(CONTAINERS.keys())[0]
                        container = CONTAINERS[largest_key]
                        cartons_per_layer = max(math.floor(container['length']/carton_l) * math.floor(container['width']/carton_w), math.floor(container['length']/carton_w) * math.floor(container['width']/carton_l))
                        num_layers = math.floor(container['height'] / carton_h)
                        total_fit = cartons_per_layer * num_layers
                        if total_fit == 0: raise Exception("A single carton is too large for any container.")
                        recommended_containers[largest_key] = recommended_containers.get(largest_key, 0) + 1
                        cartons_left_to_ship -= total_fit
                
                final_recommendation_str = " & ".join([f"{count} x {CONTAINERS[key]['name']}" for key, count in sorted(recommended_containers.items(), reverse=True)])
                final_results = {'recommendation': final_recommendation_str, 'pallet_configs': [f"Total cartons ({total_cartons}) will be floor-loaded."]}
            
            else: # Palletized
                pallet_l, pallet_w, pallet_h = float(form_inputs['pallet_l']), float(form_inputs['pallet_w']), float(form_inputs['pallet_h'])
                max_pallet_h = float(form_inputs['max_pallet_h'])
                
                cartons_per_layer = max(math.floor(pallet_l / carton_l) * math.floor(pallet_w / carton_w), math.floor(pallet_l / carton_w) * math.floor(pallet_w / carton_l))
                if cartons_per_layer == 0: raise ValueError("Carton is larger than the pallet base.")

                layers_A = math.floor((max_pallet_h - pallet_h) / carton_h)
                if layers_A <= 0: raise ValueError("Cannot build a base pallet within warehouse height limit.")
                pallet_configs = { 'l': pallet_l, 'w': pallet_w, 'Base': {'layers': layers_A, 'cartons': layers_A * cartons_per_layer, 'height': round((layers_A * carton_h) + pallet_h, 2)} }
                
                temp_container = CONTAINERS[list(CONTAINERS.keys())[0]]
                remaining_space = temp_container['height'] - pallet_configs['Base']['height']
                layers_B = math.floor((remaining_space - pallet_h) / carton_h) if remaining_space > pallet_h else 0
                if layers_B > 0:
                    pallet_configs['Topper'] = {'layers': layers_B, 'cartons': layers_B * cartons_per_layer, 'height': round((layers_B * carton_h) + pallet_h, 2)}

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
                    pallet_configs['Remnant'] = {'layers': layers_remnant, 'cartons': cartons_to_assign, 'height': round((layers_remnant * carton_h) + pallet_h, 2)}
                    total_pallet_inventory['Remnant'] = 1
                
                pallets_left_to_ship = total_pallet_inventory.copy()
                container_manifests = []
                while sum(pallets_left_to_ship.values()) > 0:
                    best_fit_container = None
                    for key, container in reversed(list(CONTAINERS.items())):
                        pallets_that_fit = simulate_single_container_load(container, pallets_left_to_ship, pallet_configs)
                        if len(pallets_that_fit) == sum(pallets_left_to_ship.values()):
                            best_fit_container = key
                            break
                    if best_fit_container:
                        manifest = Counter(pallets_left_to_ship.keys())
                        container_manifests.append({'key': best_fit_container, 'manifest': dict(manifest)})
                        pallets_left_to_ship = {}
                    else:
                        largest_key = list(CONTAINERS.keys())[0]
                        largest_container = CONTAINERS[largest_key]
                        pallets_packed_this_round = simulate_single_container_load(largest_container, pallets_left_to_ship, pallet_configs)
                        if not pallets_packed_this_round: raise Exception("Shipment is impossible; remaining pallets do not fit.")
                        manifest = Counter(pallets_packed_this_round)
                        container_manifests.append({'key': largest_key, 'manifest': dict(manifest)})
                        for p_type, count in manifest.items():
                            pallets_left_to_ship[p_type] -= count

                # Format Results with per-container weight
                total_pallets_built = sum(total_pallet_inventory.values())
                container_counts = Counter(c['key'] for c in container_manifests)
                final_recommendation_str = " & ".join([f"{count} x {CONTAINERS[key]['name']}" for key, count in sorted(container_counts.items(), reverse=True)])
                
                detailed_configs = []
                is_overweight = False
                for i, c in enumerate(container_manifests):
                    container_weight = 0
                    for p_type, count in c['manifest'].items():
                        container_weight += pallet_configs[p_type]['cartons'] * carton_weight
                    
                    if container_weight > ROAD_WEIGHT_LIMIT_KG:
                        is_overweight = True
                    
                    container_detail = {
                        'name': f"Container {i+1}: {CONTAINERS[c['key']]['name']}",
                        'weight': round(container_weight, 2),
                        'items': []
                    }
                    for p_type, count in sorted(c['manifest'].items(), key=lambda item: pallet_configs[item[0]]['height'], reverse=True):
                        conf = pallet_configs[p_type]
                        desc = f"{count} pallet(s) with {conf['layers']} layers ({conf['height']} cm) holding {conf['cartons']} cartons"
                        container_detail['items'].append(desc)
                    detailed_configs.append(container_detail)

                final_results = {'total_pallets': total_pallets_built, 'pallet_configs': detailed_configs, 'recommendation': final_recommendation_str}
            
            # Global Weight Check
            total_cargo_weight = total_cartons * carton_weight
            final_results['total_weight_kg'] = round(total_cargo_weight, 2)
            if 'total_pallets' in final_results and is_overweight:
                final_results['weight_status'] = "OVERWEIGHT"
                final_results['recommendation'] += " (WARNING: At least one container is overweight!)"
            else:
                final_results['weight_status'] = "OK"

            context['results'] = final_results
            return render_template('index.html', **context)

        except Exception as e:
            context['error'] = f"Calculation Error: {e}"
            return render_template('index.html', **context)

    return render_template('index.html', **context)

if __name__ == '__main__':
    app.run(debug=True)
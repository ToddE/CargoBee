import math
from flask import Flask, render_template, request

app = Flask(__name__)

# Constants remain the same
ROAD_WEIGHT_LIMIT_KG = 19950 
CONTAINERS = {
    '40ft_HC': {'name': "40' High Cube", 'length': 1203, 'width': 235, 'height': 269},
    '40ft': {'name': "40' Standard", 'length': 1203, 'width': 235, 'height': 239},
    '20ft': {'name': "20' Standard", 'length': 590, 'width': 235, 'height': 239}
}

# Helper function is unchanged
def simulate_single_container_load(container, pallet_inventory, pallet_configs):
    pallets_to_load = pallet_inventory.copy()
    floor_slots = max(math.floor(container['length']/pallet_configs['l']) * math.floor(container['width']/pallet_configs['w']), math.floor(container['length']/pallet_configs['w']) * math.floor(container['width']/pallet_configs['l']))
    pallets_that_fit = []
    for _ in range(floor_slots):
        remaining_h = container['height']
        while True:
            best_pallet_to_add = None
            for p_type in sorted(pallets_to_load.keys(), key=lambda k: pallet_configs[k]['height'], reverse=True):
                if pallets_to_load[p_type] > 0 and pallet_configs[p_type]['height'] <= remaining_h:
                    best_pallet_to_add = p_type
                    break
            if best_pallet_to_add:
                pallets_that_fit.append(best_pallet_to_add)
                pallets_to_load[best_pallet_to_add] -= 1
                remaining_h -= pallet_configs[best_pallet_to_add]['height']
            else: break
    return pallets_that_fit

# --- NEW MERGED ROUTE ---
# This single function now handles both displaying the form (GET) and calculating (POST)
@app.route('/', methods=['GET', 'POST'])
def home():
    form_inputs = request.form.copy() if request.method == 'POST' else request.args.copy()
    
    # If the page is loaded with a POST request (form submission), run the calculation
    if request.method == 'POST':
        try:
            # (The entire calculation logic from the previous calculate() function goes here)
            shipment_type = form_inputs.get('shipment_type')
            total_cartons = int(form_inputs['total_cartons'])
            carton_l, carton_w, carton_h = float(form_inputs['carton_l']), float(form_inputs['carton_w']), float(form_inputs['carton_h'])
            carton_weight = float(form_inputs['carton_weight'])
            
            final_results = {}

            if shipment_type == 'floor_loaded':
                cartons_left_to_ship = total_cartons
                recommended_containers = {}
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
                
                final_recommendation_str = " & ".join([f"{count} x {CONTAINERS[key]['name']}" for key, count in recommended_containers.items()])
                final_results = {'recommendation': final_recommendation_str, 'pallet_configs': [f"Total cartons ({total_cartons}) will be floor-loaded."]}
            
            else: # Palletized
                pallet_l, pallet_w, pallet_h = float(form_inputs['pallet_l']), float(form_inputs['pallet_w']), float(form_inputs['pallet_h'])
                max_pallet_h = float(form_inputs['max_pallet_h'])
                cartons_per_layer = max(math.floor(pallet_l / carton_l) * math.floor(pallet_w / carton_w), math.floor(pallet_l / carton_w) * math.floor(pallet_w / carton_l))
                if cartons_per_layer == 0: raise ValueError("Carton is larger than the pallet base.")
                layers_A = math.floor((max_pallet_h - pallet_h) / carton_h)
                if layers_A <= 0: raise ValueError("Cannot build a base pallet within warehouse height limit.")
                pallet_configs = { 'l': pallet_l, 'w': pallet_w, 'Base': {'layers': layers_A, 'cartons': layers_A * cartons_per_layer, 'height': round((layers_A * carton_h) + pallet_h, 2)} }
                total_pallet_inventory = {}
                num_base_pallets = total_cartons // pallet_configs['Base']['cartons']
                if num_base_pallets > 0: total_pallet_inventory['Base'] = num_base_pallets
                remaining_cartons = total_cartons % pallet_configs['Base']['cartons']
                if remaining_cartons > 0:
                    layers_remnant = math.ceil(remaining_cartons / cartons_per_layer)
                    pallet_configs['Remnant'] = {'layers': layers_remnant, 'cartons': remaining_cartons, 'height': round((layers_remnant * carton_h) + pallet_h, 2)}
                    total_pallet_inventory['Remnant'] = 1
                pallets_left_to_ship = total_pallet_inventory.copy()
                recommended_containers = {}
                while sum(pallets_left_to_ship.values()) > 0:
                    found_fit = False
                    for key, container in CONTAINERS.items():
                        temp_configs = pallet_configs.copy()
                        remaining_space = container['height'] - temp_configs['Base']['height']
                        layers_B = math.floor((remaining_space - pallet_h) / carton_h) if remaining_space > pallet_h else 0
                        if layers_B > 0: temp_configs['Topper'] = {'layers': layers_B, 'cartons': layers_B * cartons_per_layer, 'height': round((layers_B * carton_h) + pallet_h, 2)}
                        pallets_that_fit_list = simulate_single_container_load(container, pallets_left_to_ship, temp_configs)
                        if len(pallets_that_fit_list) == sum(pallets_left_to_ship.values()):
                            recommended_containers[key] = recommended_containers.get(key, 0) + 1
                            pallets_left_to_ship = {}
                            found_fit = True
                            break
                    if not found_fit:
                        largest_container_key = list(CONTAINERS.keys())[0]
                        container = CONTAINERS[largest_container_key]
                        temp_configs = pallet_configs.copy()
                        remaining_space = container['height'] - temp_configs['Base']['height']
                        layers_B = math.floor((remaining_space - pallet_h) / carton_h) if remaining_space > pallet_h else 0
                        if layers_B > 0: temp_configs['Topper'] = {'layers': layers_B, 'cartons': layers_B * cartons_per_layer, 'height': round((layers_B * carton_h) + pallet_h, 2)}
                        pallets_to_pack = simulate_single_container_load(container, pallets_left_to_ship, temp_configs)
                        if not pallets_to_pack: raise Exception("A single pallet is too large for any container.")
                        recommended_containers[largest_container_key] = recommended_containers.get(largest_container_key, 0) + 1
                        for p_type in pallets_to_pack: pallets_left_to_ship[p_type] -= 1
                
                total_pallets_built = sum(total_pallet_inventory.values())
                pallet_config_summary = []
                for p_type, count in total_pallet_inventory.items():
                    conf = pallet_configs[p_type]
                    desc = f"{count} pallet(s) with {conf['layers']} layers ({conf['height']} cm) holding {conf['cartons']} cartons"
                    pallet_config_summary.append(desc)
                final_recommendation_str = " & ".join([f"{count} x {CONTAINERS[key]['name']}" for key, count in recommended_containers.items()])
                final_results = {'total_pallets': total_pallets_built, 'pallet_configs': pallet_config_summary, 'recommendation': final_recommendation_str}

            total_cargo_weight = total_cartons * carton_weight
            num_containers = sum(recommended_containers.values())
            weight_limit = num_containers * ROAD_WEIGHT_LIMIT_KG
            final_results['total_weight_kg'] = round(total_cargo_weight, 2)
            if total_cargo_weight > weight_limit:
                final_results['weight_status'] = f"OVERWEIGHT by {round(total_cargo_weight - weight_limit, 2)} kg"
                final_results['recommendation'] += " (WARNING: Overweight!)"
            else:
                final_results['weight_status'] = "OK"

            return render_template('index.html', containers=CONTAINERS, results=final_results, form_inputs=form_inputs)

        except Exception as e:
            return render_template('index.html', containers=CONTAINERS, error=f"Calculation Error: {e}", form_inputs=form_inputs)

    # If the page is loaded with a GET request, just display the page
    # The JavaScript will handle populating the form from URL args
    return render_template('index.html', containers=CONTAINERS, form_inputs=form_inputs)

if __name__ == '__main__':
    app.run(debug=True)
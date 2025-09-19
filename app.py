import math
from flask import Flask, render_template, request
import os 

app = Flask(__name__)

# ---Read version from an environment variable ---
# Defaults to '1.0.0' if the variable isn't set (for local development)
APP_VERSION = os.getenv('APP_VERSION', '0.0.1-local')

# Constants
ROAD_WEIGHT_LIMIT_KG = 19950 
CONTAINERS = {
    '40ft_HC': {'name': "40' High Cube", 'length': 1203, 'width': 235, 'height': 269},
    '40ft': {'name': "40' Standard", 'length': 1203, 'width': 235, 'height': 239},
    '20ft': {'name': "20' Standard", 'length': 590, 'width': 235, 'height': 239}
}

def calculate_floor_slots(container, pallet_l, pallet_w):
    slots_v1 = math.floor(container['length'] / pallet_l) * math.floor(container['width'] / pallet_w)
    slots_v2 = math.floor(container['length'] / pallet_w) * math.floor(container['width'] / pallet_l)
    return max(slots_v1, slots_v2)

@app.route('/', methods=['GET', 'POST'])
def home():
    form_inputs = request.form.copy() if request.method == 'POST' else request.args.copy()
    
    if request.method == 'POST':
        try:
            # --- Get All Inputs ---
            shipment_type = form_inputs.get('shipment_type')
            total_cartons = int(form_inputs['total_cartons'])
            carton_l, carton_w, carton_h = float(form_inputs['carton_l']), float(form_inputs['carton_w']), float(form_inputs['carton_h'])
            carton_weight = float(form_inputs['carton_weight'])
            
            final_results = {}

            # --- Floor-Loaded Calculation ---
            if shipment_type == 'floor_loaded':
                # (This logic is unchanged and correct)
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

            # --- Palletized Calculation (New Robust Logic) ---
            else:
                pallet_l, pallet_w, pallet_h = float(form_inputs['pallet_l']), float(form_inputs['pallet_w']), float(form_inputs['pallet_h'])
                max_pallet_h = float(form_inputs['max_pallet_h'])
                cartons_per_layer = max(math.floor(pallet_l / carton_l) * math.floor(pallet_w / carton_w), math.floor(pallet_l / carton_w) * math.floor(pallet_w / carton_l))
                if cartons_per_layer == 0: raise ValueError("Carton is larger than the pallet base.")
                
                layers_A = math.floor((max_pallet_h - pallet_h) / carton_h)
                if layers_A <= 0: raise ValueError("Cannot build a base pallet within warehouse height limit.")
                cartons_A = layers_A * cartons_per_layer
                
                final_recommendation_str = "Requires multiple containers."
                
                for key, container in CONTAINERS.items():
                    floor_slots = calculate_floor_slots(container, pallet_l, pallet_w)
                    
                    # Define Topper Pallet based on this specific container
                    remaining_space = container['height'] - ((layers_A * carton_h) + pallet_h)
                    layers_B = math.floor((remaining_space - pallet_h) / carton_h) if remaining_space > pallet_h else 0
                    cartons_B = layers_B * cartons_per_layer

                    # Calculate the number of each stack type we can make
                    cartons_to_load = total_cartons
                    num_stacks = 0
                    num_base_only = 0
                    
                    if layers_B > 0:
                        num_stacks = cartons_to_load // (cartons_A + cartons_B)
                        cartons_to_load %= (cartons_A + cartons_B)
                    
                    num_base_only = cartons_to_load // cartons_A
                    cartons_to_load %= cartons_A
                    
                    num_remnant = 1 if cartons_to_load > 0 else 0
                    
                    # Check if this configuration fits in the container's floor space
                    if (num_stacks + num_base_only + num_remnant) <= floor_slots:
                        final_recommendation_str = f"1 x {container['name']}"
                        
                        # Build summary for display
                        pallet_config_summary = []
                        total_pallets = 0
                        
                        height_A = round((layers_A * carton_h) + pallet_h, 2)
                        pallet_config_summary.append(f"{num_stacks + num_base_only} pallet(s) with {layers_A} layers ({height_A} cm) holding {cartons_A} cartons")
                        total_pallets += num_stacks + num_base_only
                        
                        if num_stacks > 0 and layers_B > 0:
                            height_B = round((layers_B * carton_h) + pallet_h, 2)
                            pallet_config_summary.append(f"{num_stacks} pallet(s) with {layers_B} layers ({height_B} cm) holding {cartons_B} cartons")
                            total_pallets += num_stacks
                            
                        if num_remnant > 0:
                            layers_remnant = math.ceil(cartons_to_load / cartons_per_layer)
                            height_remnant = round((layers_remnant * carton_h) + pallet_h, 2)
                            pallet_config_summary.append(f"1 pallet(s) with {layers_remnant} layers ({height_remnant} cm) holding {cartons_to_load} cartons")
                            total_pallets += 1
                        
                        final_results = {'total_pallets': total_pallets, 'pallet_configs': pallet_config_summary, 'recommendation': final_recommendation_str}
                        break # Found the best single container, stop searching
                
                # If the loop finishes, no single container was found. This part needs multi-container logic, which is very complex.
                # For now, we will just show the total pallet breakdown.
                if not final_results:
                    num_base_pallets = total_cartons // cartons_A
                    cartons_left = total_cartons % cartons_A
                    num_remnant_pallets = 1 if cartons_left > 0 else 0
                    total_pallets = num_base_pallets + num_remnant_pallets
                    
                    pallet_config_summary = []
                    height_A = round((layers_A * carton_h) + pallet_h, 2)
                    pallet_config_summary.append(f"{num_base_pallets} pallet(s) with {layers_A} layers ({height_A} cm) holding {cartons_A} cartons")
                    if num_remnant_pallets > 0:
                        layers_remnant = math.ceil(cartons_left / cartons_per_layer)
                        height_remnant = round((layers_remnant * carton_h) + pallet_h, 2)
                        pallet_config_summary.append(f"1 pallet(s) with {layers_remnant} layers ({height_remnant} cm) holding {cartons_left} cartons")
                    
                    # A simple multi-container estimate
                    slots_per_40hc = calculate_floor_slots(CONTAINERS['40ft_HC'], pallet_l, pallet_w)
                    num_containers_needed = math.ceil(total_pallets / slots_per_40hc)
                    final_recommendation_str = f"Estimated {num_containers_needed} x 40' High Cube (or equivalent)"

                    final_results = {'total_pallets': total_pallets, 'pallet_configs': pallet_config_summary, 'recommendation': final_recommendation_str}


            total_cargo_weight = total_cartons * carton_weight
            # Simple weight check for now, can be expanded for multi-container
            weight_limit = ROAD_WEIGHT_LIMIT_KG
            final_results['total_weight_kg'] = round(total_cargo_weight, 2)
            if total_cargo_weight > weight_limit:
                final_results['weight_status'] = f"OVERWEIGHT by {round(total_cargo_weight - weight_limit, 2)} kg per container"
                final_results['recommendation'] += " (WARNING: Overweight!)"
            else:
                final_results['weight_status'] = "OK"

            return render_template('index.html', containers=CONTAINERS, results=final_results, form_inputs=form_inputs, version=APP_VERSION)

        except Exception as e:
            return render_template('index.html', containers=CONTAINERS, error=f"Calculation Error: {e}", form_inputs=form_inputs, version=APP_VERSION)

    return render_template('index.html', containers=CONTAINERS, form_inputs=request.args, version=APP_VERSION)


if __name__ == '__main__':
    app.run(debug=True)
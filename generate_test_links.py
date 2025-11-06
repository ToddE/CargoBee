import urllib.parse

# --- Configuration ---
BASE_URL = "http://127.0.0.1:5000/"

# --- Test Case Definitions ---

test_cases = [
    {
        "name": "1. Standard Load (Palletized)",
        "params": {
            "shipment_type": "palletized",
            "total_cartons": "1200",
            "carton_l": "40",
            "carton_w": "30",
            "carton_h": "25",
            "carton_weight": "15",
            "pallet_l": "120",
            "pallet_w": "100",
            "pallet_h": "15",
            "pallet_weight": "20",
            "max_pallet_h": "160"
        }
    },
    {
        "name": "2. Heavy Cartons (Weight Limit Test)",
        "params": {
            "shipment_type": "palletized",
            "total_cartons": "800",
            "carton_l": "40",
            "carton_w": "30",
            "carton_h": "25",
            "carton_weight": "25", # Heavy
            "pallet_l": "120",
            "pallet_w": "100",
            "pallet_h": "15",
            "pallet_weight": "20",
            "max_pallet_h": "160"
        }
    },
    {
        "name": "3. Large Cartons (Volume Limit Test)",
        "params": {
            "shipment_type": "palletized",
            "total_cartons": "500",
            "carton_l": "60", # Large
            "carton_w": "50", # Large
            "carton_h": "40",
            "carton_weight": "10",
            "pallet_l": "120",
            "pallet_w": "100",
            "pallet_h": "15",
            "pallet_weight": "20",
            "max_pallet_h": "180"
        }
    },
    {
        "name": "4. Small Cartons (Many Layers Test)",
        "params": {
            "shipment_type": "palletized",
            "total_cartons": "5000",
            "carton_l": "20", # Small
            "carton_w": "15", # Small
            "carton_h": "10", # Small
            "carton_weight": "2",
            "pallet_l": "120",
            "pallet_w": "100",
            "pallet_h": "15",
            "pallet_weight": "20",
            "max_pallet_h": "170"
        }
    },
    {
        "name": "5. Huge Shipment (Multi-Container Test)",
        "params": {
            "shipment_type": "palletized",
            "total_cartons": "4000", # Very large quantity
            "carton_l": "40",
            "carton_w": "30",
            "carton_h": "25",
            "carton_weight": "12",
            "pallet_l": "120",
            "pallet_w": "100",
            "pallet_h": "15",
            "pallet_weight": "20",
            "max_pallet_h": "160"
        }
    },
    {
        "name": "6. Floor-Loaded Shipment",
        "params": {
            "shipment_type": "floor_loaded",
            "total_cartons": "1500",
            "carton_l": "40",
            "carton_w": "30",
            "carton_h": "25",
            "carton_weight": "12"
        }
    }
]

def generate_links():
    """Generates and prints the share links for all test cases."""
    print("--- CargoBee Test Links ---")
    for case in test_cases:
        query_string = urllib.parse.urlencode(case["params"])
        url = f"{BASE_URL}?{query_string}"
        print(f"\n{case['name']}:")
        print(url)
    print("\n--- End of Test Links ---")

if __name__ == "__main__":
    generate_links()
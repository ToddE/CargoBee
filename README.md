[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org) 
[![Framework](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com/) 
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)



# ![CargoBee Logo](https://github.com/CargoBee/static/cargobeelogo2.svg) CargoBee
CargoBee is a logistics tool focused on solving a critical challenge: optimally loading palletized cargo into shipping containers. It calculates multi-container shipment plans by generating mixed-height pallet configurations that respect both warehouse and container constraints, helping to maximize cubic space and prevent costly errors.

### [**➡️ Go to the Live Application**](https://CargoBee.fly.dev)

## **✨ Core Capabilities**
CargoBee is a shipment planning assistant that provides a detailed and actionable loading plan.

- **Multi-Container Planning:** Automatically calculates the total number of containers required for a large shipment and provides a detailed manifest for each one.
- **Dual-Constraint Optimization:** Creates an intelligent mix of tall "Base Pallets" (to maximize warehouse height) and shorter "Topper Pallets" (for vertical stacking inside containers).
- **Weight & Safety Compliance:** Calculates the total weight for each container—including pallets—and warns if the load exceeds standard road limits.
- **Dynamic Pallet Configuration:** Determines the most efficient 2D layout of cartons on a pallet and the optimal number of layers for each distinct pallet type.
- **Profile Management:** Save and load different shipment profiles directly in your browser using local storage for quick and repeatable calculations.

## **🧠 How It Works: The Loading Strategy**

The core of CargoBee is its ability to create two different types of pallets to solve the "Two Ceilings" problem—the conflict between the maximum pallet height in the warehouse versus the internal height of a shipping container.

1. **Base Pallets:** These are built to be as tall as possible without exceeding your specified **warehouse height limit**. They are the primary, most common pallet type for any given shipment.
2. **Topper Pallets:** These are intentionally built shorter. Their height is calculated based on the space *remaining* above a Base Pallet inside a specific container, allowing for efficient double-stacking.

The algorithm then fills containers by prioritizing the most space-efficient combinations first (full stacks of Base \+ Topper pallets), ensuring a dense and stable load.

## **🛠️ Technology Stack**

CargoBee is built with a modern, reliable technology stack, ready for production.

- **Backend:** Python 3.12 with the Flask web framework.
- **Frontend:** Tailwind CSS for a clean, responsive user interface.
- **WSGI Server:** Gunicorn for robust production performance.
- **Containerization:** Docker, defined by the Dockerfile in this repository.
- **Hosting:** Deployed on the Fly.io global application platform.

## **💻 Local Development**

Want to run or contribute to CargoBee on your own machine? Follow these steps.

1. **Clone the Repository:**  
  ```bash
  git clone \[https://github.com/your-username/CargoBee.git\](https://github.com/your-username/CargoBee.git)  
  cd CargoBee
  ```
  
2. **Create and Activate a Virtual Environment:**  
    ```bash
  \# Ensure you have Python 3.12 installed  
  python3 \-m venv venv  
  source venv/bin/activate
  ```
  
3. **Install Dependencies:**  
  pip install \-r requirements.txt
  
4. **Run the Development Server:**  
  python app.py
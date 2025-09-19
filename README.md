# ConTetris 🧩

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python) ![Framework](https://img.shields.io/badge/Flask-3.x-black?logo=flask) ![License](https://img.shields.io/badge/License-MIT-green)


**ConTetris** is a simple web-based logistics calculator designed to solve the common puzzle of optimally loading cargo into shipping containers. 

It accounts for **cargo weight**, **warehouse constraints**, and **multi-container shipments**, providing an actionable loading plan beyond simple volume calculations.

---

## ✨ Live Demo

You can try out the live version of ConTetris right here:

➡️ **[https://contetris.onrender.com](https://contetris.onrender.com)** *(Link will be active once deployed)*

---

## ## Key Features

* **Dual Shipment Modes:** Calculates optimal loads for both **Palletized** and **Floor-Loaded** cargo.
* **Intelligent Palletization:** For palletized shipments, it generates a sophisticated mix of multi-height "Base" and "Topper" pallets to maximize cubic space while respecting warehouse height limits.
* **Weight & Volume Aware:** The algorithm validates the final plan against both the container's physical volume and the practical **road weight limits** (~44,000 lbs / 19,950 kg) to prevent overweight shipments.
* **Multi-Container Logic:** If a shipment is too large for any single container, ConTetris provides a smart, cost-effective recommendation of multiple containers (e.g., "1 x 40' HC & 1 x 20' Standard").
* **Persistent Profiles:** Save, name, load, and delete multiple shipment configurations directly in your browser's local storage for quick recall.
* **Shareable Calculations:** Generate a unique, transparent URL that pre-populates the calculator with your exact inputs, making it easy to share over email or text.

---

## How to Use ConTetris
ConTetris is designed for both quick estimates and detailed planning.


1.  **Choose Shipment Type:** Select **Palletized** or **Floor-Loaded**. The required input fields will adjust automatically.
2.  **Enter Shipment Details:**
    * **Total Cartons & Weight:** The total number of cartons and the weight of a single carton.
    * **Dimensions:** Provide dimensions for your cartons and, if applicable, your pallets and maximum warehouse stacking height.
3.  **Calculate & Review:**
    * Click **"Calculate Optimal Load"**. The results pane will display the most efficient combination of containers.
    * Review the **Weight Status** to ensure your load is compliant with road limits.
    * Check the **Configuration Details** for a breakdown of how many pallets to build or a confirmation of the floor load.
4.  **Share or Save:**
    * Click **"Copy Shareable Link"** to get a URL that you can send to colleagues.
    * Click **"Save to Browser"** to name and store the current inputs as a profile for future use.

---
## Run and Develop Locally
To run ConTetris on your own machine? It's easy to get started.

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/ToddE/contetris.git](https://github.com/ToddE/contetris.git)
    cd contetris
    ```
2.  **Create and Activate a Virtual Environment:**
    ```bash
    # For Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the Application:**
    ```bash
    python app.py
    ```
5.  Open your browser and go to `http://127.0.0.1:5000` or `http://localhost:5000`

---

## Contribute & Get Involved

This project was built to solve a real-world problem. Your input can make it even better!

* **Got an idea or found a bug?** Please [**open an issue**](https://github.com/ToddE/ConTetris/issues) on GitHub. We'd love to hear your feedback on new features or improvements.
* **Want to contribute code?** We welcome co-development support! Feel free to fork the repository, make your changes, and submit a pull request.

---
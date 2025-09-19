# Contetriqs 🧩

**Contetriqs** is a smart web-based logistics calculator designed to solve the complex puzzle of fitting the maximum number of cartons into a shipping container. By respecting both warehouse storage constraints and container dimensions, it generates an optimal loading plan with mixed-height pallets to maximize cubic space and reduce shipping costs.

-----

## ✨ Live Demo

You can try out the live version of Contetriqs right here:

➡️ **[https://contetriqs.onrender.com](https://www.google.com/search?q=https://contetriqs.onrender.com)** *(Link will be active once deployed)*

-----

## \#\# How to Use the App

Using Contetriqs is simple. The tool is designed to guide you from your product dimensions to a complete container loading plan.

1.  **Container Goal:** Select the specific container you plan to use, or choose **"Auto-Recommend Smallest"** to have Contetriqs find the most efficient option for you.
2.  **Total \# of Cartons to Ship:** Enter the total quantity of cartons in your shipment.
3.  **Carton Dimensions (cm):** Provide the outer length, width, and height of a single carton.
4.  **Pallet Dimensions (cm):** Enter the dimensions of your pallets. The default is a standard 120x100 cm pallet with a height of 15 cm.
5.  **Max Pallet Height (cm):** This is a critical constraint. Enter the **maximum allowable height of a loaded pallet** as determined by your warehouse racking or internal handling limits.
6.  **Click "Calculate Optimal Load":** The results will appear on the right, showing the recommended container, the total number of pallets required, and a detailed breakdown of the pallet configurations (e.g., how many pallets will be tall "Base" pallets and how many will be shorter "Topper" pallets).

-----

## \#\# 🚀 Features & Roadmap

Contetriqs is an evolving tool. Here's what it currently does and what we're thinking about for the future.

### \#\#\# Current Features

  * Calculates the most efficient 2D arrangement of cartons on a pallet.
  * Generates a sophisticated loading plan with mixed "Base" and "Topper" pallet heights.
  * Simultaneously respects both warehouse height limits and container ceiling heights.
  * Determines the total number of pallets required for a shipment.
  * Recommends the smallest possible container to fit all goods.

### \#\#\# Future Ideas

  * Incorporate carton and pallet weight for load balancing.
  * Visualize the final container load in 3D.
  * Support for multiple different carton sizes in a single shipment.
  * Save and export loading plans as PDFs.

-----

## \#\# 🤝 Contribute & Get Involved

This project was built to solve a real-world problem, and your input can make it even better\!

  * **Got an idea or found a bug?** Please [**open an issue**](https://www.google.com/search?q=https://github.com/your-username/contetriqs/issues) on GitHub. We'd love to hear your feedback on new features or improvements.
  * **Want to contribute code?** We welcome co-development support\! Feel free to fork the repository, make your changes, and submit a pull request.

-----

## \#\# 💻 Local Development

Want to run Contetriqs on your own machine? It's easy to get started.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/contetriqs.git
    cd contetriqs
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
5.  Open your browser and go to `http://127.0.0.1:5000`.

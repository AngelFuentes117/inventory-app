# Inventory App

A simple web-based inventory management application built with **Flask** and **SQLite**.

## Features

- **Add products** with name, description, category, price, quantity, and location
- **List products** with search by name and filter by category
- **Edit and delete** products
- **Adjust stock** (in/out movements) with movement history tracking
- **Low stock alerts** - visual warning when quantity drops below 5
- **Dashboard** showing total products, total inventory value, and low-stock items
- Data stored in **SQLite** (`inventory.db`)
- Clean, simple Spanish-language web interface
- Runs on **port 5001** (http://127.0.0.1:5001)

## Requirements

- Python 3.8+
- Flask 3.x

## Installation

1. Clone or navigate to the project directory:
   ```bash
   cd inventory-app
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

```bash
python app.py
```

The app will be available at **http://127.0.0.1:5001**

The database (`inventory.db`) and tables are created automatically on first run.

## Database Schema

- **products**: id, name, description, category, price, quantity, location, created_at, updated_at
- **movements**: id, product_id, type (in/out), quantity, reason, created_at

## Project Structure

```
inventory-app/
├── app.py              # Main Flask application
├── schema.sql          # Database schema (CREATE TABLE IF NOT EXISTS)
├── requirements.txt    # Python dependencies
├── .gitignore          # Git ignore rules
├── README.md           # This file
└── templates/          # Jinja2 templates
    ├── base.html       # Base template
    ├── index.html      # Dashboard
    ├── products.html   # Product list
    ├── product_form.html  # Add/Edit product form
    ├── adjust_form.html   # Stock adjustment form
    └── movements.html     # Movement history
```

## Usage

1. **Dashboard** - View overview stats and low-stock alerts
2. **Products** - Browse, search, and filter products
3. **Add Product** - Create new inventory items
4. **Edit/Delete** - Modify or remove products
5. **Adjust Stock** - Record stock in/out movements with reasons
6. **Movements** - View complete movement history per product

## License

MIT License - Feel free to use and modify for your needs.
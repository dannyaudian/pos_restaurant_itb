🍽️ POS Restaurant ITB
A comprehensive Frappe application designed for modern restaurant management, built on ERPNext v15. Supporting multi-branch operations, dynamic menu customization, and integrated kitchen workflow systems.

🧩 Core Modules
POS Order Management
Feature-rich order entry system allowing waiters to create and modify orders with support for item variants and dynamic attributes.

Table Management
Track and allocate tables across multiple restaurant branches with status monitoring and availability checks.

Kitchen Order Ticket (KOT)
Automated ticket generation system that routes orders from POS to kitchen departments.

Kitchen Display System (KDS)
Real-time order tracking display showing active orders by table and processing status.

Kitchen Station
Specialized displays for specific kitchen departments (grill, fry, etc.) showing only relevant items grouped by item group.

Printer Mapping
Flexible configuration for routing tickets to the appropriate kitchen or receipt printers.

🌍 Multi-Branch Architecture
All core documents include branch-based isolation to support multi-location restaurant operations:

Data and configurations are segmented by branch
Active branch validation throughout workflow
Branch-specific printer configurations
User roles and permissions with branch context
🧾 POS Order
Key Features
Automatic order_id generation using branch code and sequential numbering
Smart item selection focused on Item Templates
Dynamic attribute UI for variant selection
Structured order status workflow
Real-time calculation of order totals
Status Flow
Draft → In Progress → Ready for Billing → Paid / Cancelled
Item Handling
Items are selected from Item Templates
For variant items, attributes are presented in a dialog
Selected attributes generate the correct variant automatically
Both the variant item_code and selected dynamic_attributes are stored
🍽️ Dynamic Attributes System
Implementation
The system leverages ERPNext's native Item Variant framework with a custom UI layer:

User selects an Item Template in POS Order
System detects has_variant = 1 and presents attribute options
Selected attributes resolve to a specific Item Variant
Both variant (item_code) and attributes (dynamic_attributes) are stored
Data Structure
Dynamic attributes are stored as JSON in this format:

[
  {"attribute_name": "Spice Level", "attribute_value": "Medium"},
  {"attribute_name": "Toppings", "attribute_value": "Extra Cheese"}
]
Attribute Summary
A computed property transforms the JSON into a human-readable string:

Spice Level: Medium, Toppings: Extra Cheese
🍳 Kitchen Order Ticket (KOT)
Automation
Created automatically when items are sent to kitchen
after_insert
 hook triggers creation of KDS and Kitchen Station entries
Dynamic attributes are preserved throughout the workflow
Status Management
New → In Progress → Ready → Served / Cancelled
Structure
Each KOT references the source POS Order
Contains KOT Items that track individual dish preparation
Preserves all dynamic attributes for kitchen reference
📺 Kitchen Display System (KDS)
Function
Aggregates KOTs by table for kitchen overview
Updates status in real-time based on item preparation progress
Provides clear view of all active orders
Implementation
Created automatically from KOT via hooks
Bidirectional sync with KOT status
Branch-isolated to show only relevant orders
🔪 Kitchen Station
Function
Created per item (one entry per quantity unit)
Filtered by item group for department-specific views
Preserves attribute details for accurate preparation
Configuration
The Kitchen Station Setup doctype defines:

Which item groups route to which stations
Which printers receive tickets from each station
Branch-specific configurations and print formats
🖨️ Printing System
Print Routing
Each Kitchen Station can have multiple assigned printers
Different print formats for different printer types
Support for network, USB, and Bluetooth printers
Print Formats
KOT Print: Detailed ticket for kitchen preparation
Receipt: Customer-facing bill format
Custom formats configurable per station
⚙️ Technical Architecture
API Structure
RESTful endpoints in api/ directory
Function-specific files (e.g., create_kot.py, resolve_variant.py)
Proper whitelist protections via @frappe.whitelist()
Hook Integration
Document event hooks for automated workflows
Client-side JS customizations for enhanced UI
Custom permissions handling for role-based access
Helper Functions
Common utilities in utils/ directory
Shared functions for attribute handling
Reusable components for consistency
🔄 Complete Workflow
POS Order Creation
    ↓
Item & Attribute Selection
    ↓
Send to Kitchen → Generate KOT
    ↓
KOT after_insert → Create KDS
    ↓
KOT after_insert → Create Kitchen Station Items
    ↓
Kitchen Processing → Status Updates
    ↓
Ready for Billing → Payment → Finalization
🧪 Development and Testing
Branch Isolation
All operations validate branch context to ensure data security and proper segregation.

Error Handling
Comprehensive try-except patterns with detailed error logging throughout the codebase.

Validation
Extensive validation at each step ensures data integrity and prevents common operational errors.

🚀 Deployment
The application is designed for flexible deployment options:

Frappe Cloud: One-click deployment with managed infrastructure
Self-hosted VPS: Complete control with custom server configuration
Development: Local setup with bench for testing and customization
CI/CD pipelines via GitHub Actions support automated testing and deployment.

This application follows Frappe/ERPNext v15 best practices and maintains a modular architecture for enhanced maintainability and extensibility. All components are designed to work together seamlessly while allowing for independent customization as needed.